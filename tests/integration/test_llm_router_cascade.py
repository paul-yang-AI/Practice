from unittest.mock import patch

import litellm
import pytest
from pydantic import BaseModel

from shared_harness.llm_router import complete
from shared_harness.schemas.common import BoundaryDecision


class _Confidence(BaseModel):
    confidence: float


@pytest.mark.integration
def test_llm_router_cascade_high_confidence_skips_tier2() -> None:
    """Tier1 confidence check does not invoke Tier2 arbiter path in router."""
    with patch("shared_harness.llm_router.litellm.completion") as mock_completion:
        mock_completion.return_value = _mock_response('{"confidence": 0.99}')
        result = complete(
            tier=1,
            call_site="sec_confidence_tier1",
            messages=[{"role": "user", "content": "rate confidence"}],
            schema=_Confidence,
            run_id=None,
            task_type="filing",
        )
        assert isinstance(result, _Confidence)
        assert result.confidence == 0.99
        assert mock_completion.call_count == 1


@pytest.mark.integration
def test_llm_router_fallback_tier2_on_primary_429() -> None:
    primary = "gemini/gemini-2.0-flash"
    fallback = "openrouter/openai/gpt-4o-mini"

    def side_effect(*args, **kwargs):
        model = kwargs.get("model") or args[0]
        if model == primary:
            raise litellm.exceptions.RateLimitError("429", "gemini", "primary")
        return _mock_response(
            '{"start": 10, "end": 200, "confidence": 0.88, "source_quote": null}'
        )

    with patch("shared_harness.llm_router.litellm.completion", side_effect=side_effect):
        with patch.dict(
            "os.environ",
            {
                "LLM_TIER2_PRIMARY": primary,
                "LLM_TIER2_FALLBACK": fallback,
                "LLM_FALLBACK_ENABLED": "true",
                "OPENROUTER_API_KEY": "test-key-for-mock",
            },
        ):
            from shared_harness import llm_config

            llm_config.TIER_MAP[2] = llm_config.TierConfig(
                primary=primary, fallback=fallback
            )
            result = complete(
                tier=2,
                call_site="sec_boundary_arbiter",
                messages=[{"role": "user", "content": "arbiter"}],
                schema=BoundaryDecision,
                run_id=None,
                task_type="filing",
            )
    assert isinstance(result, BoundaryDecision)
    assert result.confidence == 0.88


@pytest.mark.integration
def test_llm_router_no_fallback_on_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    from shared_harness import cost_tracker
    from shared_harness.cost_tracker import BudgetExceededError
    from shared_harness.job_store import create_run

    monkeypatch.setattr(
        cost_tracker,
        "_limits",
        lambda: cost_tracker.BudgetLimits(
            global_budget_usd=100.0,
            max_llm_calls_filing=1,
        ),
    )
    run_id = create_run("filing")

    with patch("shared_harness.llm_router.litellm.completion") as mock_completion:
        mock_completion.return_value = _mock_response('{"start": 0, "end": 10, "confidence": 0.5}')
        complete(
            tier=2,
            call_site="sec_boundary_arbiter",
            messages=[{"role": "user", "content": "first"}],
            schema=BoundaryDecision,
            run_id=run_id,
            task_type="filing",
        )
        with pytest.raises(BudgetExceededError):
            complete(
                tier=2,
                call_site="sec_boundary_arbiter",
                messages=[{"role": "user", "content": "second"}],
                schema=BoundaryDecision,
                run_id=run_id,
                task_type="filing",
            )
        assert mock_completion.call_count == 1


@pytest.mark.integration
def test_llm_router_primary_only_no_fallback_on_success() -> None:
    with patch("shared_harness.llm_router.litellm.completion") as mock_completion:
        mock_completion.return_value = _mock_response('{"start": 0, "end": 50, "confidence": 0.95}')
        result = complete(
            tier=2,
            call_site="sec_boundary_arbiter",
            messages=[{"role": "user", "content": "ok"}],
            schema=BoundaryDecision,
            run_id=None,
            task_type="filing",
        )
        assert isinstance(result, BoundaryDecision)
        assert mock_completion.call_count == 1
        assert mock_completion.call_args.kwargs.get("model") or mock_completion.call_args[1].get("model")


def _mock_response(text: str):
    class Usage:
        prompt_tokens = 10
        completion_tokens = 20

    class Message:
        content = text

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]
        usage = Usage()

    return Response()
