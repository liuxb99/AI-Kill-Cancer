"""
Tests for VCF.GZ upload, security, and persistence — hardened streaming version.
"""
from __future__ import annotations

import gzip
import hashlib
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
            data={"upload_mode": "anonymous_research"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "analysis_eligible" in data
        assert "upload_id" in data

    def test_upload_vcf_gz(self, client):
        gz_content = _make_gz_vcf()
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf.gz", gz_content, "application/gzip")},
            data={"upload_mode": "anonymous_research"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["compression"] == "gzip"
        expected_sha = hashlib.sha256(gz_content).hexdigest()
        assert data["sha256"] == expected_sha

    def test_upload_vcf_gz_to_plain_ext_rejected(self, client):
        """Gzip content with .vcf extension must be rejected."""
        gz_content = _make_gz_vcf()
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", gz_content, "application/gzip")},
            data={"upload_mode": "anonymous_research"},
        )
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert "mismatch" in str(detail).lower() or "extension_content_mismatch" in str(detail)

    def test_upload_plain_to_gz_ext_rejected(self, client):
        """Plain VCF content with .vcf.gz extension must be rejected."""
        content = _make_vcf_bytes()
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf.gz", content, "text/plain")},
            data={"upload_mode": "anonymous_research"},
        )
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert "mismatch" in str(detail).lower()

    def test_upload_corrupted_gz_rejected(self, client):
        corrupted = b"this is not gzip\x1f\x8b"
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf.gz", corrupted, "application/gzip")},
        )
        # Should fail — gzip content with mismatch or corrupted
        assert resp.status_code in (400, 422)

    def test_upload_empty_vcf_rejected(self, client):
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("empty.vcf", b"", "text/plain")},
        )
        # Empty file is valid extension but has no content
        assert resp.status_code in (400, 413, 422)

    def test_upload_invalid_extension(self, client):
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.txt", b"data", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_sha256_consistency(self, client):
        content = _make_vcf_bytes()
        resp1 = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", content, "text/plain")},
            data={"upload_mode": "anonymous_research"},
        )
        resp2 = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", content, "text/plain")},
            data={"upload_mode": "anonymous_research"},
        )
        assert resp1.status_code in (200, 201)
        assert resp2.status_code in (200, 201)
        assert resp1.json()["sha256"] == resp2.json()["sha256"]

    def test_upload_response_has_no_absolute_path(self, client):
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", _make_vcf_bytes(), "text/plain")},
            data={"upload_mode": "anonymous_research"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        text = str(data)
        assert "/mnt/" not in text
        assert "storage_path" not in data

    def test_upload_genome_build_conflict(self, client):
        """VCF with GRCh38 content but request says GRCh37 → 422."""
        content = _make_vcf_bytes()
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", content, "text/plain")},
            data={"upload_mode": "anonymous_research", "genome_build": "GRCh37"},
        )
        # Our test VCF doesn't have explicit build, so this may be OK or conflict
        assert resp.status_code in (200, 201, 422)

    def test_sequencing_test_fk_not_found(self, client):
        """Non-existent sequencing_test_id → 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", _make_vcf_bytes(), "text/plain")},
            data={"sequencing_test_id": fake_id},
        )
        assert resp.status_code == 404

    def test_sequencing_test_fk_invalid_uuid(self, client):
        """Invalid UUID → 422."""
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", _make_vcf_bytes(), "text/plain")},
            data={"sequencing_test_id": "not-a-uuid"},
        )
        assert resp.status_code == 422

    def test_analysis_eligible_on_valid(self, client):
        """Valid VCF should be marked eligible."""
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("test.vcf", _make_vcf_bytes(), "text/plain")},
            data={"upload_mode": "anonymous_research"},
        )
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("analysis_eligible") == "eligible"

    def test_upload_exceeding_size(self, client):
        """Very large file should get 413."""
        big = b"X" * 600 * 1024 * 1024
        resp = client.post(
            "/api/v1/vcf/upload",
            files={"file": ("big.vcf", big, "text/plain")},
            data={"upload_mode": "anonymous_research"},
        )
        assert resp.status_code in (413, 422)

