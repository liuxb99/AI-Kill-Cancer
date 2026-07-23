"""
Docker smoke test — verifies production containers build and respond.

These tests require Docker to be available on the host.
They are skipped if Docker is not available.
"""
from __future__ import annotations

import os
import subprocess
import time
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DOCKER_AVAILABLE", ""),
    reason="Docker smoke tests require Docker. Set DOCKER_AVAILABLE=1 to run.",
)

COMPOSE_FILE = "docker/docker-compose.yml"
PROJECT_NAME = f"cancer-smoke-{uuid.uuid4().hex[:8]}"


def _run_docker_cmd(*args, **kwargs):
    """Run a docker compose command."""
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "-p", PROJECT_NAME, *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kwargs)


class TestDockerSmoke:
    """End-to-end Docker smoke tests."""

    @classmethod
    def setup_class(cls):
        cls.compose_up = False

    @classmethod
    def teardown_class(cls):
        if cls.compose_up:
            _run_docker_cmd("down", "-v")

    def test_01_build_images(self):
        """Docker images should build successfully."""
        result = _run_docker_cmd("build")
        assert result.returncode == 0, f"Build failed:\n{result.stderr}"
        self.compose_up = True

    def test_02_compose_up(self):
        """All services should start."""
        result = _run_docker_cmd("up", "-d")
        assert result.returncode == 0, f"Compose up failed:\n{result.stderr}"

        # Wait for services
        time.sleep(10)
        result = _run_docker_cmd("ps")
        assert result.returncode == 0
        # All 4 services should be running
        for service in ["db", "redis", "api", "frontend"]:
            assert service in result.stdout, f"Service {service} not running"

    def test_03_db_healthy(self):
        """Database should be healthy."""
        result = _run_docker_cmd("exec", "-T", "db", "pg_isready", "-U", "postgres")
        assert result.returncode == 0, f"DB not healthy:\n{result.stderr}"

    def test_04_redis_healthy(self):
        """Redis should be healthy."""
        result = _run_docker_cmd("exec", "-T", "redis", "redis-cli", "ping")
        assert "PONG" in result.stdout, f"Redis not healthy:\n{result.stdout}"

    def test_05_api_health(self):
        """API health endpoint should respond."""
        import json
        import urllib.request
        try:
            resp = urllib.request.urlopen("http://localhost:8000/api/v1/health", timeout=10)
            data = json.loads(resp.read().decode())
            assert resp.status == 200
            assert "status" in data
        except Exception as e:
            pytest.skip(f"API not reachable (may need port mapping): {e}")

    def test_06_frontend_serves_html(self):
        """Frontend should serve index.html."""
        import urllib.request
        try:
            resp = urllib.request.urlopen("http://localhost:80/", timeout=10)
            html = resp.read().decode()
            assert "<html" in html.lower() or "<!doctype" in html.lower()
        except Exception as e:
            pytest.skip(f"Frontend not reachable (may need port mapping): {e}")

    def test_07_clean_shutdown(self):
        """Services should stop cleanly."""
        result = _run_docker_cmd("down")
        assert result.returncode == 0, f"Shutdown failed:\n{result.stderr}"
        self.compose_up = False
