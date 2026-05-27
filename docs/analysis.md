# Analysis Report

> This report treats the LLM as an unstable reasoning engine; `shared_harness` + the pytest
> pyramid constitute the **Harness** (context scaffolding, contract linting, entropy sensing).
> Aligned with [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/):
> **Agent = Model + Harness** — this project implements the MVI scope, with evidence from
> `reports/eval_train.csv` and L1 tests, not claims of industrial-grade Codex automation.

All numbers below come from `reports/eval_train.csv` unless marked *estimated*.

---

## Correctness Validation

### Task 2 — SEC 10-K

- **Span integrity (Tier0 main path)**: `body[start:end] == text` enforced before store.
  Violation → `low_confidence` or fail fast. LLM arbiter adjusts boundary only.
- **Token conservation**: median `token_ratio_p50` across train filings = **0.99**
  (input segment ≈ output text; no forced summarization).
- **Char coverage**: mean = **0.88** (extracted items cover 88% of body by char offset).
- **Gold boundary**: 3 filings × 6–7 gold items each; **P95 boundary error = 0 chars**
  (exact match on synthetic fixtures).
- **Required items recall**: **4/4** for every train filing (Items 1, 1A, 7, 8).
- **Incorporation handling**: Citi Items 10–14 correctly flagged `incorporated_by_reference`
  with `text=None` — no hallucinated content.

### Task 1 — Browser Agent

- **Multi-step LLM planning**: Step 0 navigates; steps 1+ use Tier1 LLM to plan actions
  (click, type, scroll, etc.) and extract task-specific results.
- **L0 every-step verify**: heuristic URL/content check; `silent_failure` definition =
  L0 passed but task actually not done. Target: 0. **Measured: 0** (train split).
- **Blind Critic (optional)**: independent Tier1 YES/NO on final a11y tree;
  `ENABLE_BLIND_CRITIC=true`. Not agent self-reflection.
  L2 `test_verify_blind_critic_gate` confirms: critic NO → run fails.
- **`compress_a11y` budget**: max 12000 chars (≈3000 tokens); L1 `test_a11y_tree_truncation`.
- **`cancel_event`**: checked each step; `finally: browser.close()`. L2 `test_agent_graceful_shutdown`.
- **Recovery strategy table**: classified by `FailureType`; same type never repeats same
  strategy; L1 `test_recovery_routing` + L2 `test_agent_recovery_loop`.
- **Result extraction**: When LLM sets `done=true`, it extracts task-specific results from
  the page state (e.g., top story title, search results, page data).

**Live evaluation results (6 train tasks, real Chromium headless + LLM planning):**

| task_id | domain | type | steps | status |
|---------|--------|------|-------|--------|
| smoke_example_title | example.com | navigate | 2 | success |
| smoke_httpbin_headers | httpbin.org | extract | 2 | success |
| wikipedia_search | wikipedia.org | search | 3-4 | success |
| github_navigate_repo | github.com | navigate | 2 | success |
| hacker_news_top | news.ycombinator.com | extract | 2 | success |
| duckduckgo_search | duckduckgo.com | search | 3-4 | success |

- **Success rate**: 6/6 (100%) — LLM-planned multi-step execution handles search/interact tasks
- **Silent failures**: 0 (L0 verify + LLM done-gate correctly reject incomplete tasks)
- **P50 latency**: 2.5s; **P95 latency**: 5.0s (includes LLM planning calls)
- **Cost per task**: ~$0.001–0.003 (1-3 Tier1 LLM calls per task × Gemini Flash pricing)
- **LLM calls per task**: 1–3 (plan + done verification)
- **Recovery steps triggered**: 0 on current train set (LLM plans correct actions first time)

---

## Failure Mode Analysis (FMA)

Failures classified by rule-based mapping in `eval_runner` and agent loop; numbers from CSV.

| Category | Definition | Mapping Examples |
|----------|-----------|-----------------|
| **Data Schema Drift** | Input structure/format variance | TOC broken, regex miscut, `low_confidence`, span fail |
| **Reasoning Failure** | Model/strategy reasoning error | arbiter boundary error, `verify_critic_reject`, recovery exhausted |
| **Infrastructure** | External dependency/resource | EDGAR 429, litellm fallback, `BudgetExceeded`, SQLite locked |

### Task 2 — Train Split Results

| Ticker | failure_category | Notes |
|--------|-----------------|-------|
| MSFT | `ok` | Clean Tier0; 8 items extracted, 0 LLM calls |
| INTC | `ok` | iXBRL normalized; 6 items extracted, 0 LLM calls |
| C | `ok` | 5 extracted + 5 incorporated; 0 LLM calls |

**Tier0 coverage**: 100% of train filings processed with zero LLM token cost ($0.00/filing).

### Task 1 — Expected Failure Modes (from tasks.yaml)

| task_id | target_failure | Mitigation |
|---------|---------------|------------|
| `wikipedia_search` | `ELEMENT_NOT_FOUND` | role+name → scroll → relax selector |
| `github_navigate_repo` | `TIMEOUT` | extend wait → simplify DOM |
| `duckduckgo_search` | `ACTION_NO_EFFECT` | click parent → press Enter |

---

## Hybrid Pipeline vs End-to-End LLM

### Why not send the entire 10-K to a large model?

**10-K E2E Risks:**
- Long-context "Lost in the Middle" → Item 7/8 recall drops for middle segments
- Model tendency toward Forced Summarization → table/footnote data loss
- Without ground truth, hard to detect "looks complete but missing numbers"

**Agent E2E Risks:**
- All-LLM decisions + no verify → silent failure, infinite action loops, token burn
- Heuristic-only verify → false-positive success (page "looks right" but task incomplete)

**This System's Choice:**
- Tier0 heuristics (BS4/regex) + LLM Arbiter (disputed boundary only)
- Agent: L0 every-step verify + optional Blind Critic terminal gate
- Post-validation: span integrity, token conservation, char coverage, Gold + Silver

### Cost / Recall Comparison

| Approach | $/filing (P50) | Required Item Recall | Auditable |
|----------|---------------|---------------------|-----------|
| E2E long-context LLM (*estimated*) | ~$0.05–0.15 (full token × rate) | Prone to summarize/miss middle | Low |
| **This system (Hybrid)** | **$0.00** (Tier0 100% train) | **4/4 required** + correct incorporation | High |

*Recall = required item exists or correctly marked `incorporated_by_reference`,
not claiming 16 items full-text 100%.*

---

## Performance Summary (from CSV)

### Task 2 — SEC 10-K

| Metric | MSFT | INTC | C |
|--------|------|------|---|
| Tier0 extracted items | 8 | 6 | 5 |
| Incorporated items | 0 | 0 | 5 |
| Missing items | 14 | 16 | 12 |
| Required recall | 4/4 | 4/4 | 4/4 |
| Token ratio P50 | 0.988 | 0.990 | 0.990 |
| Char coverage | 0.872 | 0.897 | 0.884 |
| USD/filing | $0.00 | $0.00 | $0.00 |
| Fallback used | No | No | No |

### Task 1 — Browser Agent (Live Evaluation with LLM Planning)

| Metric | Value |
|--------|-------|
| Tasks in manifest | 8 (6 train, 2 heldout) |
| Domains covered | 6 |
| Task types | navigate, search, extract, form |
| **Train success rate** | **6/6 (100%)** |
| **Silent failures** | **0** |
| **P50 latency** | **2.5s** |
| **P95 latency** | **5.0s** |
| **$/task** | **~$0.002** (1-3 Tier1 Gemini Flash calls) |
| **LLM calls/task** | 1–3 (plan + done) |
| Max steps/task | 10 |
| Max LLM calls/task | 5 |
| Recovery budget | 2 attempts/step, no repeat strategy |
| Per-task cost cap | $0.50 |
| Global budget | $20 |

**Output types**: Agent now extracts task-specific results (e.g., page title, top story text,
search result snippets) rather than just reporting pass/fail status.

---

## Observability

- `cost_events` table: every LLM call with `run_id`, `tier`, `provider`, `model`, `call_site`, `attempt`, `tokens_in/out`, `usd`
- `run_steps` table: every agent step with `failure_type`, `recovery_strategy`, `log_json`
- `reports/eval_train.csv`: reproducible eval output with `failure_category`
- Circuit breaker: `BudgetExceededError` → zero API calls; never fallback after budget hit
