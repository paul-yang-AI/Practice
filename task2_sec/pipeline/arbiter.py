"""Tier2 boundary arbiter — adjusts offsets only, never rewrites body."""

from __future__ import annotations

from shared_harness.llm_router import complete
from shared_harness.prompt_loader import load_prompt
from shared_harness.schemas.common import BoundaryDecision


def arbitrate_boundary(
    *,
    body: str,
    chunk_start: int,
    chunk_end: int,
    item_id: str,
    run_id: str | None = None,
    context_tokens: int = 500,
) -> BoundaryDecision:
    """Call Tier2 LLM to resolve disputed item boundary within local chunk."""
    # ~4 chars per token heuristic
    char_window = context_tokens * 4
    win_start = max(0, chunk_start - char_window // 2)
    win_end = min(len(body), chunk_end + char_window // 2)
    chunk = body[win_start:win_end]

    system = load_prompt("boundary_arbiter")
    user = (
        f"Item: {item_id}\n"
        f"Chunk offsets in full body: [{win_start}:{win_end}]\n"
        f"Current boundary: start={chunk_start}, end={chunk_end}\n\n"
        f"CHUNK:\n{chunk}"
    )
    decision = complete(
        tier=2,
        call_site="sec_boundary_arbiter",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        schema=BoundaryDecision,
        run_id=run_id,
        task_type="filing",
    )
    assert isinstance(decision, BoundaryDecision)

    if decision.source_quote and decision.source_quote not in chunk:
        decision = decision.model_copy(update={"source_quote": None})

    # Map relative offsets if arbiter returns chunk-relative (absolute expected in schema)
    if decision.start < win_start or decision.end > len(body):
        # Treat as chunk-relative adjustment
        rel_start = win_start + decision.start if decision.start < char_window else decision.start
        rel_end = win_start + decision.end if decision.end < char_window else decision.end
        decision = decision.model_copy(update={"start": rel_start, "end": rel_end})

    return decision
