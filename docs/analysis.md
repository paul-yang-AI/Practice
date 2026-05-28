# Analysis Report

> This report treats the LLM as an unstable reasoning engine; `shared_harness` + the pytest
> pyramid constitute the **Harness** (context scaffolding, contract linting, entropy sensing).
> Aligned with [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/):
> **Agent = Model + Harness** — evidence from `reports/eval_train.csv`, `reports/eval_summary.json`,
> and L1/L2/L3 tests.

All numbers below come from **`reports/eval_train.csv`** (generated `2026-05-28`) unless marked *estimated*.

---

## Correctness Validation

### Task 2 — SEC 10-K

- **Span integrity (Tier0 main path)**: `body[start:end] == text` enforced before store.
- **Token conservation**: MSFT/INTC/C median `token_ratio_p50` = **0.9879–0.9899**.
- **Char coverage** (vs full body): MSFT **0.87**, INTC **0.86**, C **1.00** (section-name fallback on Citi).
- **Gold boundary**: train filings P95 boundary error = **0 chars** on committed gold set.
- **Required items recall**: MSFT/INTC **4/4**; Citi **3/3** (Items 1A, 7, 8).
- **Incorporation**: INTC Items 10–14 + Citi Items 10–14 → `incorporated_by_reference`, `text=None`.
- **Section-name fallback**: Business, Properties, Legal Proceedings, Mine Safety, Cybersecurity, and 12 more standard 10-K section titles mapped for filings without "Item N" headers.
- **Tier0 coverage**: **100%** train filings at **$0.00/filing** (zero LLM on eval path).

### Task 1 — Browser Agent

- **Multi-step LLM planning**: Step 0 navigate → steps 1+ plan/act with `AgentAction.result`.
- **L0 every-step verify** + optional **Blind Critic** (`ENABLE_BLIND_CRITIC=true`; default **false** on Zeabur; L2 `test_verify_blind_critic_gate` green).
- **Recovery**: classified `FailureType` → strategy table; max 2 recovery/step; L1 `test_recovery_routing`.
- **Silent failures**: **0** on latest train CSV (no success without extracted result on extract/search tasks).
- **Held-out policy**: `tasks.yaml` heldout tasks + SEC BRK.B in `reports/heldout_snapshot.json` — not used for tuning.

**Latest live eval (6 train tasks, Chromium headless + Gemini Tier1, no OPENROUTER key):**

| task_id | status | steps | llm_calls | usd | failure_category |
|---------|--------|-------|-----------|-----|------------------|
| smoke_example_title | success | 2 | 1 | $0.0005 | ok |
| smoke_httpbin_headers | failed | 19 | 5 | $0.0058 | max_steps |
| wikipedia_search | failed | 18 | 5 | $0.0127 | max_steps |
| github_navigate_repo | success | 3 | 2 | $0.0060 | ok |
| hacker_news_top | success | 2 | 1 | $0.0033 | ok |
| duckduckgo_search | failed | 18 | 5 | $0.0137 | max_steps |

From `reports/eval_summary.json`:
- **Success rate**: **3/6 (50%)**
- **Silent failures**: **0**
- **P50 latency**: **27.0s**; **P95**: **57.7s**
- **P50 cost**: **$0.0059/task**
- **Recovery steps (total)**: **25**

Navigate/extract tasks (example.com, HN, GitHub) succeed reliably. Multi-step search (Wikipedia, DuckDuckGo) often hits **max_steps=10** under Gemini-only (no OpenRouter fallback). Setting `OPENROUTER_API_KEY` improves resilience when primary JSON parse fails.

---

## Failure Mode Analysis (FMA)

| Category | Definition | Train examples (CSV) |
|----------|-----------|----------------------|
| **Data Schema Drift** | Input format variance | SEC: `toc_header_agreement` 0.64 on Citi |
| **Reasoning Failure** | Strategy/planning error | Agent: `max_steps` on search tasks |
| **Infrastructure** | External deps / budget | Agent: `infrastructure` when DNS/LLM unavailable; `budget_exceeded` demo in `scripts/demo_circuit_breaker.py` |

### Task 2 — Train Split (SEC)

| Ticker | required | extracted | incorporated | missing | failure_category |
|--------|----------|-----------|--------------|---------|------------------|
| MSFT | 4/4 | 8 | 0 | 14 | ok |
| INTC | 4/4 | 17 | 5 | 0 | ok |
| C | 3/3 | 12 | 5 | 5 | ok |

### Task 1 — Train Split (Agent)

| failure_category | count |
|------------------|-------|
| ok | 3 |
| max_steps | 3 |

Top mitigation: classified recovery (not blind retry), `max_steps=10` circuit, optional OpenRouter fallback, Blind Critic terminal gate.

---

## Hybrid Pipeline vs End-to-End LLM

| Approach | $/unit (P50, CSV) | Recall / quality | Auditable |
|----------|-------------------|------------------|-----------|
| E2E long-context LLM (*estimated*) | ~$0.05–0.15/filing | Prone to summarize/miss middle | Low |
| **SEC Hybrid (this repo)** | **$0.00** | Required items 100% train | High (span integrity) |
| E2E browser agent (*estimated*) | ~$0.01–0.05/task | Silent failure risk | Low |
| **Agent Hybrid (this repo)** | **~$0.006** | 50% train (3/6); silent_failure=0 | High (L0 + optional Critic) |

---

## Held-Out Snapshot (not tuned)

From `reports/heldout_snapshot.json` (local run):

| Ticker | Accession | required | extracted | failure |
|--------|-----------|----------|-----------|---------|
| BRK.B | 0000950170-25-025210 | 4/4 | 21 | ok |

---

## Observability

- `cost_events`: per LLM call with `run_id`, `tier`, `call_site`, `attempt`, `usd`
- `run_steps`: agent steps with `failure_type`, `recovery_strategy`, `extracted_result` in log JSON
- `reports/eval_train.csv`: SEC + agent unified eval export
- `reports/eval_summary.json`: aggregate metrics for analysis
- Circuit breaker demo: `python scripts/demo_circuit_breaker.py` → `BudgetExceededError` at $0.001 cap

---

## Performance Summary

### Task 2 — SEC 10-K (from CSV)

| Metric | MSFT | INTC | C |
|--------|------|------|---|
| Required recall | 4/4 | 4/4 | 3/3 |
| Tier0 extracted | 8 | 17 | 12 |
| Incorporated | 0 | 5 | 5 |
| Token ratio P50 | 0.9875 | 0.9970 | 0.9819 |
| Char coverage (full body) | 0.87 | 0.86 | 1.00 |
| USD/filing | $0.00 | $0.00 | $0.00 |

### Task 1 — Browser Agent (from eval_summary.json)

| Metric | Value |
|--------|-------|
| Train tasks | 6 |
| Success rate | 50% (3/6) |
| Silent failures | 0 |
| P50 latency | 27.0s |
| P95 latency | 57.7s |
| P50 cost | $0.0059 |
| LLM calls (total run) | 19 |
| Max steps/task | 10 |
| Max LLM calls/task | 25 |
| Max primary retries | 2 |
| Global budget | $20 (`RUN_BUDGET_USD`) |
