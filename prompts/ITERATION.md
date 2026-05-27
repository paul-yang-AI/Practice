# Prompt Iteration Log

Record v1→v2 changes with Failed Path / Resolution / Validation.

## boundary_arbiter: v1 → v2 (regex fallback + prompt hardening)

- **Failed Path**: Initial regex `ITEM\s+\d+` matched inline cross-references like
  "see Item 1 above" as segment headers, causing false boundary splits mid-paragraph.
  Additionally, `v1_boundary_arbiter.txt` lacked explicit constraint against summarization,
  leading to potential token ratio violations when arbiter is invoked.
- **Resolution**: Anchored `HEADER_RE` to line-start (`(?m)^[ \t]*`) in `segment.py`;
  added negative-sample assertions in `test_regex_boundary_fallback.py` to reject
  body-inline mentions. Longer item IDs match first (e.g. "10" before "1").
  Promoted to `prompts/v2_boundary_arbiter.txt` adding: ratio constraint (≥0.85),
  trailing whitespace rule, and explicit negative constraints for numerical preservation.
- **Validation**: `test_regex_boundary_fallback` green — negative sample
  `"see Item 1 above"` no longer produces a segment hit; `pytest -m unit` all pass.

## incorporation_by_reference: Citi Items 10–14

- **Failed Path**: Pipeline initially reported Items 10–14 as `extracted` with full text
  that was actually just a one-line incorporation notice, misleading eval metrics.
- **Resolution**: Added `detect_incorporation()` in `task2_sec/pipeline/incorporation.py`
  using regex to detect "incorporated by reference" language; status set to
  `incorporated_by_reference` with `text=None` to avoid hallucinating content.
- **Validation**: `test_item_status::test_incorporation_by_reference_no_fake_fulltext` green;
  `test_sec_manifest_citi_incorporation` confirms Items 10 and 14 correctly flagged.

## agent_recovery: v1 → v2 (classified routing vs blind retry)

- **Failed Path**: Initial agent design used a generic `try/except → retry` loop. Same
  recovery action was attempted repeatedly (e.g. re-clicking the same missing element),
  burning LLM calls without progress and triggering `MaxLLMCalls` breaker.
  `v1_recovery.txt` was a flat instruction with no failure-type awareness.
- **Resolution**: Introduced `FailureType` enum + `STRATEGY_TABLE` in `recovery.py`.
  `get_next_strategy(failure_type, attempted)` returns the next *untried* strategy;
  `MAX_RECOVERY_PER_STEP = 2` caps retries. `prompt_loader.load_prompt("recovery",
  variant=failure_type)` injects the matching SOP fragment from `prompts/sops/recovery.md`.
  Promoted to `prompts/v2_recovery.txt` with per-failure-type strategy options,
  explicit "do NOT repeat" constraint, and JSON-only output format.
- **Validation**: `test_recovery_routing` (9 assertions) green — `ACTION_NO_EFFECT` returns
  different strategies on each call; exhausted strategies return `None`; `CAPTCHA_OR_LOGIN`
  always returns `blocked`. L2 `test_agent_recovery_loop` confirms recovery→success and
  exhaustion→failed paths work end-to-end.
  New L2 `test_verify_blind_critic_gate` confirms critic NO → run fails (silent_failure=0).
