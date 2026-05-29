# Whaleforce Coding Test — PLAN (Phase 0–3)

> Full spec: see project plan. This is the tactical summary for daily execution.

## Goal

Monorepo with **task1_agent/** (browser agent), **task2_sec/** (10-K pipeline), **shared_harness/** (LLM router, cost, EDGAR, job store).

## Phase Gates

| Phase | Deliver | Gate |
|-------|---------|------|
| **0** | Scaffold + harness stubs + Docker smoke | `pytest -m unit` green; `test_llm_parse`; Playwright smoke |
| **1** | SEC fetch→segment→validate→UI | L1 SEC tests; `test_sec_manifest`; CSV ≥3 rows |
| **2** | Agent loop + recovery + Refresh UI | `test_recovery_routing`; 2 smoke tasks |
| **3** | README, ITERATION, analysis, Zeabur | L3 train CSV; Harness docs |

**Rule**: Phase 1 before Phase 2. L1 never cut. Commit at each phase gate.

## Architecture

- **Frontend**: Streamlit multi-page, single Dockerfile (Playwright base image)
- **LLM**: litellm only; Tier0 = rules/BS4 (zero token); Tier1/2 via `llm_router`
- **SEC**: all HTTP via `edgar_client.py`; cache at `task2_sec/eval/cache/`
- **Agent**: sync Playwright in background thread; DB + Refresh (no SSE)
- **Validation**: span integrity `body[start:end]==text`; classified recovery (no blind retry)

## Day Reference

- **Day 1 (Phase 0)**: scaffold, edgar+cost+job_store, prompt_loader, test_llm_parse, Docker
- **Day 2**: normalize, segment, regex fallback (zero LLM)
- **Day 3**: validate, arbiter, llm_router fallback
- **Day 4**: gold eval, SEC UI, run_eval.py
- **Day 5–6**: agent loop, recovery, Streamlit agent page
- **Day 7**: docs, analysis FMA, deploy

## MVI Stop-Loss

If behind: keep Phase 1 CSV + L1 + 2 agent smoke; cut Blind Critic / extra L2.

## Env

```
SEC_USER_AGENT="Company Name email@domain.com"
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
RUN_BUDGET_USD=20
```

## Post-Phase-3 (P0–P3 + Eval Expansion)

| Track | Deliver | Gate |
|-------|---------|------|
| **P0** | Eval honesty — `content_quality.py`, strict required-item check | Train KPI unchanged; `toc_stub_required_item` category |
| **P1–P2** | Tier0 robustness + surgical LLM classify/arbiter | `segment_classify.py`; `run_eval.py --tier0-only` / `--with-llm` |
| **Eval expansion** | 11-filing manifest, held-out baseline scripts | `heldout_baseline.json` 5/8 ok; honest JPM/AAPL/KSCP gaps in docs |
| **Prompts audit** | `prompts/README.md`, ITERATION entries, arbiter SOP sync | Reviewer-readable AI collaboration trail |
