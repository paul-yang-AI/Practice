# Prompts Index

Versioned prompts and SOP fragments for both tasks. Reviewers: start with [ITERATION.md](ITERATION.md) for the failure → fix → validation narrative.

## Loading

`shared_harness.prompt_loader.load_prompt(name)` prefers `sops/{name}.md`, then `v1_{name}.txt`.

## Task 1 — Browser Agent (runtime)

| Prompt | File | Call site | Tier | When |
|--------|------|-----------|------|------|
| `agent_plan` | `v1_agent_plan.txt` | `task1_agent/agent/loop.py` | 1 | Each planning step (act path) |
| `agent_extract` | `v1_agent_extract.txt` | `task1_agent/agent/extract.py` | 1 | Extract-mode tasks (one-shot) |
| `blind_critic` | `v1_blind_critic.txt` | `task1_agent/agent/verify.py` | 1 | Optional gate (`ENABLE_BLIND_CRITIC`) |

Recovery is **not** LLM-driven: `task1_agent/agent/recovery.py` routes by `FailureType` to a zero-token deterministic `STRATEGY_TABLE` (see `agent_recovery` in ITERATION).

## Design docs (not invoked at agent runtime)

| Name | File | Purpose |
|------|------|---------|
| `recovery` | `sops/recovery.md` | Human-readable strategy catalog; `prompt_loader` can load variants for tests/docs only |
| *(legacy)* | `v2_recovery.txt` | LLM recovery planner spec — **deprecated**; kept for audit trail |

## Task 2 — SEC 10-K

| Prompt | File | Call site | Tier | When |
|--------|------|-----------|------|------|
| `sec_segment_fallback` | `v1_sec_segment_fallback.txt` | `task2_sec/pipeline/segment.py` | 1 | Coverage &lt; 30% or missing &gt; 5 |
| `sec_segment_classify` | `v1_sec_segment_classify.txt` | `task2_sec/pipeline/segment_classify.py` | 1 | Heuristic `UNKNOWN` + `ENABLE_SEC_LLM_CLASSIFY` |
| `boundary_arbiter` | `sops/boundary_arbiter.md` | `task2_sec/pipeline/arbiter.py` | 2 | Low-confidence boundary disputes |

Legacy: `v2_boundary_arbiter.txt` — kept in sync with `sops/boundary_arbiter.md`.

## Iteration log

See [ITERATION.md](ITERATION.md) for v1→v2 changes, eval honesty (P0), held-out expansion, UI presentation (`sec_eval_ui_presentation`), and known gaps (**AAPL 2010**, **KSCP 10-K/A**; JPM fixed in `kpi_alignment_and_jpm_header_quality`).
