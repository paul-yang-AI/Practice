# SEC Eval — Manual Spot Checks (Held-Out)

Train gold boundaries are pipeline-generated (Tier0, `use_llm_fallback=False`). Held-out filings below include **manual verification notes** to reduce circular-eval risk.

**Scope note:** This is **targeted sampling** of structurally complex held-out (and one train reference) filings to validate deterministic contracts and honest status labels — **not** an exhaustive audit of all 16 Items on every filing. Remaining held-out entries (O, NEM, GROW) rely on Tier0 baseline + span/token contracts; see `reports/heldout_baseline.json`.

## Method

1. Run Tier0 extraction locally (`use_llm_fallback=False`, `use_arbiter=False`).
2. Open the [SEC interactive viewer](https://www.sec.gov/cgi-bin/viewer) for the accession.
3. For each checked Item: confirm status (extracted / cross-ref / incorporated / missing) and that extracted text is **real prose**, not a TOC index row.
4. Record pass / partial / fail — **partial** is acceptable when status is honest (e.g. cross-ref index, K-xx pointer, incorporated by reference).

Column **Observation** records outcome after SEC viewer cross-check (or Tier0 baseline + spot read of extracted span when noted).

---

## BRK.B — `0000950170-25-025210`

| Item | Expected | Observation |
|------|----------|-------------|
| 1 | extracted or section_name anchor | ✓ Pass — Business prose extracted (required prose; not index-only) |
| 1A | cross_ref or extracted | ◐ Partial — span is `Risk Factors` + **K-24** only; `content_quality` → **cross_ref** (K-1 pointer, not full Risk Factors body) |
| 7 | cross_ref or extracted MD&A | ◐ Partial — MD&A title + **K-33** only; **cross_ref**; honest vs ✅ prose stub |
| 8 | extracted financials | ✓ Pass — long financials / auditor region (required prose) |

**Variant stressed:** K-1-style TOC, section_name fallback. Baseline: required **4/4**, `required_prose_count` **2**, `required_cross_ref_count` **2**.

---

## JPM — `0000019617-25-000270`

| Item | Expected | Observation |
|------|----------|-------------|
| 7 | extracted MD&A | ✓ Pass — real MD&A body (not front mega-TOC stub); header quality pick + period titles |
| 7A / 8 | extracted | ✓ Pass — market risk / financials regions present; baseline **4/4** required |
| 1 / 1A | extracted | ✓ Pass — in-body anchors; second-bank TOC variant (generalized Citi-style heuristics, no ticker branch) |

**Variant stressed:** second large-bank mega-TOC. Baseline: **4/4** required, `failure_category=ok`.

---

## KSCP — `0001558370-25-006009` (10-K/A amendment)

| Item | Expected | Observation |
|------|----------|-------------|
| 1, 1A, 7, 8 | missing or partial | ✗ Fail (expected) — Part III-only **10-K/A** amendment; no full Part I/II Item headers in HTML; baseline **0/4** required, `missing_item_header` |
| Part III items | extracted if present | ✓ Pass — pipeline extracts amendment body where headers exist; does not invent Part I MD&A |

**Variant stressed:** 10-K/A amendment semantics. Baseline: **0/4** required — **honest gap**, not silent success.

---

## AAPL 2010 — `0001193125-10-012091` (pre-iXBRL)

| Item | Expected | Observation |
|------|----------|-------------|
| 1 | extracted Business | ✗ Fail — legacy `<font>`/table layout; sparse Item headers; baseline **2/4** required |
| 7 | extracted MD&A | ◐ Partial — section_name may find MD&A region; required KPI still short on legacy headers |
| 8 | extracted financials | ✓ Pass — table-heavy financials region extractable when anchor found |

**Variant stressed:** pre-iXBRL HTML (2007–2010 era). Baseline: **2/4** required, `missing_item_header`.

---

## MSFT FY2020 — `0001564590-20-034944` (longitudinal)

| Item | Expected | Observation |
|------|----------|-------------|
| 1, 1A, 7, 8 | extracted | ✓ Pass — all required prose; boundaries stable vs MSFT FY2024 train filing (same issuer, older format) |

**Variant stressed:** same issuer, cross-year format drift. Baseline: **4/4** required, `failure_category=ok`.

---

## Citi — `0000831001-25-000067` (train, reference)

| Item | Expected | Observation |
|------|----------|-------------|
| 7A | ~146k chars `MARKET RISK` body | ✓ Pass — not 98-char TOC row (`70–129, …`) |
| 8 | ~697k chars auditor/financials | ✓ Pass — not TOC stub |
| 10, 14 | incorporated_by_reference | ✓ Pass — no inline text; honest incorporated status |

Included as a **train reference** anchor (verified during Citi mega-TOC iteration); not held-out KPI.

---

## Other held-out (baseline only)

| Ticker | Accession | Required | Notes |
|--------|-----------|----------|-------|
| O | `0000726728-25-000055` | 4/4 ok | REIT structure — not item-spot-checked here |
| NEM | `0001164727-25-000011` | 4/4 ok | Mining / Item 4 path |
| GROW | `0001437749-24-028889` | 4/4 ok | Compact filer |

Populate optional cache:

```bash
python scripts/cache_heldout_filings.py
python scripts/run_heldout_baseline.py
```
