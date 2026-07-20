"""
Tests for VCF.GZ upload, security, and persistence.
"""
from __future__ import annotations

import gzip
import hashlib
import os
import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.main import create_app


@pytest.fixture(scope="module")
def client():
    settings.DATABASE_URL = "sqlite+aiosqlite:///./test_vcfgz.db"
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        yield c


# ─── VCF.GZ tests ─────────────────────────────────────────────────────────────

VALID_VCF = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
1\t1000\t.\tA\tG\t30.5\tPASS\t.
7\t140753336\t.\tT\tC\t99.0\tPASS\t.
"""


def _make_gz_vcf(content: str = VALID_VCF) -> bytes:
    return gzip.compress(content.encode())


def _make_vcf_bytes(content: str = VALID_VCF) -> bytes:
    return content.encode()


class TestVCFGzUpload:
    def test_upload_vcf_plain(self, client):
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", _make_vcf_bytes(), "text/plain")},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["validation_status"] in ("valid", "invalid")

    def test_upload_vcf_gz(self, client):
        """Upload a real .vcf.gz file."""
        gz_content = _make_gz_vcf()
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf.gz", gz_content, "application/gzip")},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["compression"] == "gzip"
        assert "sha256" in data
        # SHA256 should be of original gzip bytes
        expected_sha = hashlib.sha256(gz_content).hexdigest()
        assert data["sha256"] == expected_sha

    def test_upload_corrupted_gz(self, client):
        """Corrupted gzip should fail properly."""
        corrupted = b"this is not gzip content\x1f\x8b"
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf.gz", corrupted, "application/gzip")},
        )
        # Should return error — either 400 (security) or 200 with error status
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("validation_status") == "invalid" or len(data.get("errors", [])) > 0
        else:
            assert resp.status_code in (400, 413)

    def test_upload_empty_gz(self, client):
        """Empty gzip should be rejected."""
        empty_gz = gzip.compress(b"")
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("empty.vcf.gz", empty_gz, "application/gzip")},
        )
        assert resp.status_code in (400, 422)

    def test_upload_large_file_rejected(self, client):
        """Very large file should be rejected (413)."""
        # Create content exceeding size limit
        large = b"X" * 600 * 1024 * 1024  # 600MB
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("large.vcf", large, "text/plain")},
        )
        assert resp.status_code in (413, 400)

    def test_upload_invalid_extension(self, client):
        """Non-VCF extension should be rejected."""
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.txt", b"data", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_sha256_consistency(self, client):
        """Same file uploaded twice should have same SHA256."""
        content = _make_vcf_bytes()
        resp1 = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", content, "text/plain")},
        )
        resp2 = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", content, "text/plain")},
        )
        assert resp1.status_code in (200, 201)
        assert resp2.status_code in (200, 201)
        assert resp1.json()["sha256"] == resp2.json()["sha256"]

    def test_upload_response_has_no_absolute_path(self, client):
        """Response must not contain server filesystem paths."""
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", _make_vcf_bytes(), "text/plain")},
        )
        data = resp.json() if resp.status_code < 400 else {}
        text = str(data)
        assert ":\\" not in text
        assert "/mnt/" not in text
        assert "/home/" not in text
        assert "/tmp/" not in text

    def test_upload_no_path_traversal(self, client):
        """Path traversal filename should be handled safely (UUID storage)."""
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("../../../etc/passwd.vcf", b"", "text/plain")},
        )
        # Empty file will fail validation but shouldn't cause path traversal
        assert resp.status_code in (400, 413, 200)
        if resp.status_code == 200:
            data = resp.json()
            # Storage path must not contain traversal sequences
            assert "/" not in data.get("upload_id", "")
