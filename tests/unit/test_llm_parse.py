import pytest

from shared_harness.llm_parse import parse_json_text, parse_model
from shared_harness.schemas.common import CriticVerdict


@pytest.mark.unit
def test_parse_json_text_strips_markdown_fence() -> None:
    raw = '```json\n{"passed": true}\n```'
    assert parse_json_text(raw) == '{"passed": true}'


@pytest.mark.unit
def test_parse_json_text_plain() -> None:
    assert parse_json_text('  {"a": 1}  ') == '{"a": 1}'


@pytest.mark.unit
def test_parse_model_valid() -> None:
    verdict = parse_model('{"passed": false}', CriticVerdict)
    assert verdict.passed is False


@pytest.mark.unit
def test_parse_model_invalid_raises() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        parse_model("not json", CriticVerdict)
