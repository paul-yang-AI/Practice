# SEC Eval — Manual Spot Checks (Held-Out)

Train gold boundaries are pipeline-generated (Tier0, `use_llm_fallback=False`). Held-out filings below include **manual verification notes** to reduce circular-eval risk.

## Method

1. Run Tier0 extraction locally (`use_llm_fallback=False`, `use_arbiter=False`).
2. Open the [SEC interactive viewer](https://www.sec.gov/cgi-bin/viewer) for the accession.
3. For each checked Item: confirm status (extracted / cross-ref / incorporated / missing) and that extracted text is **real prose**, not a TOC index row.
4. Record pass / partial / fail — partial is acceptable when status is honest (e.g. cross-ref index for INTC-style filings).

---

## BRK.B — `0000950170-25-025210`

| Item | Expected | Check |
|------|----------|-------|
| 1 | extracted or section_name anchor | K-1-style TOC; verify Business prose starts correctly |
| 7 | extracted MD&A | Long MD&A span; not a page-number stub |
| 1A | extracted or cross-ref | Risk Factors present or correctly labeled |
| 8 | extracted financials | Auditor report / financial statements region |

**Variant stressed:** K-1-style TOC, section_name fallback.

---

## Citi — `0000831001-25-000067` (train, reference)

| Item | Expected | Verified |
|------|----------|----------|
| 7A | ~146k chars `MARKET RISK` body | ✓ Not 98-char TOC row (`70–129, …`) |
| 8 | ~697k chars auditor/financials | ✓ Not TOC stub |
| 10, 14 | incorporated_by_reference | ✓ No inline text |

---

## AAPL 2010 — `0001193125-10-012091` (pre-iXBRL)

| Item | Expected | Check |
|------|----------|-------|
| 1 | extracted Business | Legacy HTML `<font>`/table layout |
| 7 | extracted MD&A | May rely on section_name if Item headers sparse |
| 8 | extracted financials | Table-heavy region |

**Variant stressed:** pre-iXBRL HTML (2007–2010 era).

---

## MSFT FY2020 — `0001564590-20-034944` (longitudinal)

| Item | Expected | Check |
|------|----------|-------|
| 1, 1A, 7, 8 | extracted | Compare boundary stability vs MSFT FY2024 train filing |

**Variant stressed:** same issuer, cross-year format drift.

---

## Notes on optional held-out entries

Filings marked `cache_optional: true` in `manifest.json` run in eval only when HTML exists under `task2_sec/eval/cache/`. Populate cache:

```bash
python scripts/cache_heldout_filings.py
```
