"""Unit tests for report fail-closed behavior (_get_report_and_verify_access)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.backend.api.v1.reports import _get_report_and_verify_access, SENTINEL_CASE_ID
from src.backend.domain.case_acl import CaseRole


class MockUser:
    def __init__(self, user_id=None):
        self.id = user_id or uuid.uuid4()


class MockModel:
    """Mock ClinicalReportModel with configurable case_id."""
    def __init__(self, case_id):
        self.id = uuid.uuid4()
        self.case_id = case_id


@pytest.mark.asyncio
async def test_handler_none_case_id():
    """case_id=None must raise 403 — covers the 'if not case_id_str:' branch."""
    model = MockModel(case_id=None)
    repo_mock = AsyncMock()
    repo_mock.get.return_value = model

    with patch("src.backend.api.v1.reports.ReportRepository", return_value=repo_mock):
        with pytest.raises(HTTPException) as exc:
            await _get_report_and_verify_access(
                str(model.id), MockUser(), AsyncMock(), CaseRole.VIEWER,
            )
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("error") == "access_denied"


@pytest.mark.asyncio
async def test_handler_sentinel_case_id():
    """Sentinel UUID (migration 015 quarantine) must raise 403 for all users."""
    model = MockModel(case_id=SENTINEL_CASE_ID)
    repo_mock = AsyncMock()
    repo_mock.get.return_value = model

    with patch("src.backend.api.v1.reports.ReportRepository", return_value=repo_mock):
        with pytest.raises(HTTPException) as exc:
            await _get_report_and_verify_access(
                str(model.id), MockUser(), AsyncMock(), CaseRole.VIEWER,
            )
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("error") == "access_denied"


@pytest.mark.asyncio
async def test_handler_malformed_case_id():
    """Non-UUID case_id must raise 403."""
    model = MockModel(case_id="not-a-uuid-at-all")
    repo_mock = AsyncMock()
    repo_mock.get.return_value = model

    with patch("src.backend.api.v1.reports.ReportRepository", return_value=repo_mock):
        with pytest.raises(HTTPException) as exc:
            await _get_report_and_verify_access(
                str(model.id), MockUser(), AsyncMock(), CaseRole.VIEWER,
            )
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("error") == "access_denied"


@pytest.mark.asyncio
async def test_handler_report_not_found():
    """Non-existent report ID must raise 404."""
    repo_mock = AsyncMock()
    repo_mock.get.return_value = None

    with patch("src.backend.api.v1.reports.ReportRepository", return_value=repo_mock):
        with pytest.raises(HTTPException) as exc:
            await _get_report_and_verify_access(
                str(uuid.uuid4()), MockUser(), AsyncMock(), CaseRole.VIEWER,
            )
    assert exc.value.status_code == 404
