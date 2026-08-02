"""Phase 3F-2 outbox event_id contract tests."""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from src.backend.repositories.clinical_graph_outbox_repo import (
    ClinicalGraphOutboxRepository,
)


def _payload(**overrides):
    data = {
        "aggregate_type": "treatment_plan",
        "aggregate_id": "plan-001",
        "event_type": "treatment_plan.created",
        "payload": {"plan_id": "plan-001"},
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_generates_event_id_when_omitted():
    db = Mock()
    db.flush = AsyncMock()
    repo = ClinicalGraphOutboxRepository(db)

    model = await repo.create(**_payload())

    assert str(uuid.UUID(model.event_id)) == model.event_id
    db.add.assert_called_once_with(model)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_preserves_and_trims_supplied_event_id():
    db = Mock()
    db.flush = AsyncMock()
    repo = ClinicalGraphOutboxRepository(db)

    model = await repo.create(**_payload(event_id="  event-001  "))

    assert model.event_id == "event-001"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["", "   ", "\t\n"])
async def test_create_rejects_blank_event_id(invalid):
    db = Mock()
    db.flush = AsyncMock()
    repo = ClinicalGraphOutboxRepository(db)

    with pytest.raises(ValueError, match="must not be blank"):
        await repo.create(**_payload(event_id=invalid))

    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_rejects_non_string_event_id():
    db = Mock()
    db.flush = AsyncMock()
    repo = ClinicalGraphOutboxRepository(db)

    with pytest.raises(TypeError, match="must be a string"):
        await repo.create(**_payload(event_id=123))


@pytest.mark.asyncio
async def test_create_rejects_event_id_longer_than_database_contract():
    db = Mock()
    db.flush = AsyncMock()
    repo = ClinicalGraphOutboxRepository(db)

    with pytest.raises(ValueError, match="64 characters"):
        await repo.create(**_payload(event_id="x" * 65))
