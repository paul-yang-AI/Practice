import pytest
from pydantic import ValidationError

from shared_harness.schemas.common import BoundaryDecision, CriticVerdict
from shared_harness.schemas.sec_schema import ItemRecord, ItemStatus


@pytest.mark.unit
def test_critic_verdict_requires_passed() -> None:
    with pytest.raises(ValidationError):
        CriticVerdict.model_validate({})


@pytest.mark.unit
def test_boundary_decision_end_gt_start() -> None:
    with pytest.raises(ValidationError):
        BoundaryDecision(start=10, end=5, confidence=0.5)


@pytest.mark.unit
def test_item_record_status_enum() -> None:
    item = ItemRecord(item_id="10", status=ItemStatus.INCORPORATED_BY_REFERENCE)
    assert item.text is None
