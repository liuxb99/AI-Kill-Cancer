"""
Phase 3D Async Client Tests — ClinicalGraphClient subprocess robustness.

Tests:
- CLI not found handling
- Timeout handling
- Non-zero exit code handling
- JSON parse handling (stdout is not JSON → fallback)
"""

from __future__ import annotations

import sys

import pytest

from src.backend.clinical_graph.client import ClinicalGraphClient


@pytest.mark.asyncio
async def test_cli_not_found():
    """CLI 路径不存在时应返回 success=False 及错误信息。"""
    client = ClinicalGraphClient(cli_path="/nonexistent/knowgraph")
    result = await client._run_cli(["--help"])
    assert not result.get("success")
    assert "not found" in result.get("error", "")


@pytest.mark.asyncio
async def test_timeout_handling():
    """CLI 超时应返回 success=False 及 timeout 信息。"""
    client = ClinicalGraphClient(cli_path=sys.executable, timeout=0.1)
    result = await client._run_cli(["-c", "import time; time.sleep(10)"])
    assert not result.get("success")
    assert "timeout" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_nonzero_exit_code():
    """CLI 返回非零 exit code 时应返回 success=False。"""
    client = ClinicalGraphClient(cli_path=sys.executable, timeout=5)
    result = await client._run_cli(["-c", "exit(42)"])
    assert not result.get("success")
    # 应该包含 exit code 信息
    error = result.get("error", "")
    assert "42" in error or "exit" in error or "code" in error


@pytest.mark.asyncio
async def test_json_parse_fallback():
    """CLI 输出非 JSON 文本时应返回 success=True + message（回退模式）。"""
    client = ClinicalGraphClient(cli_path=sys.executable, timeout=5)
    result = await client._run_cli(["-c", "print('hello from cli')"])
    # 非 JSON 输出 → 回退到 {"success": True, "message": ...}
    assert result.get("success")
    assert "hello from cli" in result.get("message", "")


@pytest.mark.asyncio
async def test_json_parse_success():
    """CLI 输出合法 JSON 时应直接返回解析后的字典（不包裹 success 字段）。"""
    client = ClinicalGraphClient(cli_path=sys.executable, timeout=5)
    result = await client._run_cli(["-c", "import json; print(json.dumps({'a': 1, 'b': [2, 3]}))"])
    # _run_cli 对合法 JSON 直接返回 json.loads 结果，不加 success wrapper
    assert result.get("a") == 1
    assert result.get("b") == [2, 3]


@pytest.mark.asyncio
async def test_no_stdout():
    """CLI 无 stdout 输出时应返回 success=True（空响应）。"""
    client = ClinicalGraphClient(cli_path=sys.executable, timeout=5)
    result = await client._run_cli(["-c", ""])
    assert result.get("success")
    # 无 stdout → {"success": True}
    assert "error" not in result or not result["error"]
