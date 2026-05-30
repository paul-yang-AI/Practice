"""L0 heuristic verification + Blind Critic terminal gate."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from shared_harness.llm_parse import parse_model
from shared_harness.schemas.common import CriticVerdict


@dataclass
class VerifyResult:
    passed: bool
    reason: str = ""


_ERROR_INDICATORS = [
    "this site can't be reached",
    "err_connection",
    "dns_probe",
    "net::err",
    "403 forbidden",
    "404 not found",
    "access denied",
]

_STOP_WORDS = frozenset(
    "the a an is are was were be been being have has had do does did "
    "will would shall should may might can could to of in for on with "
    "at by from and or but not no nor so yet it its that this these "
    "those there their them they we you i my me he she him her us our "
    "what which who whom whose when where how why if then than too also "
    "very just about up out into over after before above below between "
    "each all any both few more most other some such as go get make".split()
)


def _extract_task_keywords(task: str) -> list[str]:
    """Extract meaningful verification keywords from task description.

    Generic approach: extract proper nouns, domain names, and key phrases.
    No hardcoding for specific websites.
    """
    keywords = []

    urls = re.findall(r"https?://[^\s,]+", task)
    for url in urls:
        domain = urlparse(url).netloc.replace("www.", "")
        if domain:
            keywords.append(domain.split(".")[0])

    quoted = re.findall(r"['\"]([^'\"]+)['\"]", task)
    keywords.extend(quoted)

    return keywords


def verify_step(
    *,
    url: str,
    page_text: str = "",
    task: str = "",
    start_url: str = "",
    expected_url_fragment: str | None = None,
    expected_keywords: list[str] | None = None,
    check_task_keywords: bool = True,
) -> VerifyResult:
    """L0 heuristic check after each action step.

    Generic verification — no hardcoded site-specific logic.
    Set check_task_keywords=False during navigation/intermediate steps so
    goal phrases (e.g. quoted search terms) are validated only at task completion.
    """
    if not url or url == "about:blank":
        return VerifyResult(passed=False, reason="Page not loaded (blank URL)")

    lower_text = page_text.lower()
    for indicator in _ERROR_INDICATORS:
        if indicator in lower_text:
            return VerifyResult(passed=False, reason=f"Error page detected: {indicator}")

    if expected_url_fragment and expected_url_fragment not in url:
        return VerifyResult(passed=False, reason=f"URL missing fragment: {expected_url_fragment!r}")

    if start_url:
        expected_domain = urlparse(start_url).netloc.replace("www.", "")
        actual_domain = urlparse(url).netloc.replace("www.", "")
        if expected_domain and actual_domain and expected_domain != actual_domain:
            if not actual_domain.endswith(expected_domain):
                return VerifyResult(
                    passed=False,
                    reason=f"Domain mismatch: expected {expected_domain}, got {actual_domain}",
                )

    all_keywords = list(expected_keywords or [])
    if check_task_keywords and task and not all_keywords:
        all_keywords = _extract_task_keywords(task)
    if all_keywords:
        missing = [kw for kw in all_keywords if kw.lower() not in lower_text]
        if missing:
            return VerifyResult(passed=False, reason=f"Keywords not found: {missing}")

    if len(page_text.strip()) < 50:
        return VerifyResult(passed=False, reason="Page content too short (possibly empty)")

    return VerifyResult(passed=True)


def verify_navigation(*, url: str, page_text: str, start_url: str) -> VerifyResult:
    """Verify that initial navigation succeeded (step 0) — domain + load only."""
    return verify_step(
        url=url,
        page_text=page_text,
        start_url=start_url,
        check_task_keywords=False,
    )


def verify_extracted_result(extracted_result: str, page_text: str) -> VerifyResult:
    """Check that a claimed extraction appears in visible page content (anti-hallucination)."""
    result_clean = extracted_result.strip()
    if not result_clean:
        return VerifyResult(passed=False, reason="Empty extracted result")

    lower_page = page_text.lower()
    lower_result = result_clean.lower()
    if lower_result in lower_page:
        return VerifyResult(passed=True)

    compact_page = re.sub(r"\s+", " ", lower_page)
    compact_result = re.sub(r"\s+", " ", lower_result)
    if compact_result in compact_page:
        return VerifyResult(passed=True)

    tokens = [t for t in re.findall(r"[\w./@-]+", result_clean) if len(t) >= 6]
    if tokens and any(t.lower() in lower_page for t in tokens):
        return VerifyResult(passed=True)

    stripped = page_text.strip()
    if stripped.startswith("{"):
        try:
            import json

            blob = json.dumps(json.loads(stripped), ensure_ascii=False).lower()
            if compact_result in blob or any(t.lower() in blob for t in tokens):
                return VerifyResult(passed=True)
        except Exception:
            pass

    return VerifyResult(passed=False, reason="Extracted result not found in page content")


def _quoted_terms(task: str) -> list[str]:
    return re.findall(r"['\"]([^'\"]+)['\"]", task)


def _term_on_page(term: str, page_text: str, url: str) -> bool:
    lower = page_text.lower()
    url_lower = url.lower()
    term_lower = term.lower()
    if term_lower in lower or term_lower.replace(" ", "_") in url_lower:
        return True
    words = [w for w in term.split() if len(w) > 3]
    if len(words) >= 2:
        return sum(1 for w in words if w.lower() in lower) >= max(1, len(words) // 2)
    return False


def verify_task_outcome(
    *,
    task: str,
    url: str,
    page_text: str,
    extracted_result: str = "",
    start_url: str = "",
    task_type: str = "",
    success_hints: dict | None = None,
) -> VerifyResult:
    """Terminal verification when the planner declares done=true."""
    hints = success_hints or {}

    if extracted_result.strip():
        ext = verify_extracted_result(extracted_result, page_text)
        if not ext.passed:
            return ext
    else:
        min_len = 50 if "extract" in task.lower() or task_type == "extract" else 15
        if len(page_text.strip()) < min_len:
            return VerifyResult(passed=False, reason="Final page content too short")

    url_fragment = hints.get("expect_url_contains")
    if url_fragment and url_fragment.lower() not in url.lower():
        return VerifyResult(
            passed=False,
            reason=f"Final URL missing expected fragment: {url_fragment!r}",
        )

    body_fragment = hints.get("expect_body_contains")
    if body_fragment and body_fragment.lower() not in page_text.lower():
        return VerifyResult(
            passed=False,
            reason=f"Final page missing expected text: {body_fragment!r}",
        )

    quoted = _quoted_terms(task)
    if quoted:
        if not any(_term_on_page(q, page_text, url) for q in quoted):
            return VerifyResult(passed=False, reason=f"Task terms not reflected on page: {quoted}")

    if task_type == "search" and start_url:
        query_terms = [q for q in quoted if q]
        if query_terms and url.rstrip("/") == start_url.rstrip("/"):
            return VerifyResult(passed=False, reason="Search task ended on start URL without navigation")

    if start_url:
        expected_domain = urlparse(start_url).netloc.replace("www.", "")
        actual_domain = urlparse(url).netloc.replace("www.", "")
        if expected_domain and actual_domain:
            if expected_domain != actual_domain and not actual_domain.endswith(expected_domain):
                return VerifyResult(
                    passed=False,
                    reason=f"Final URL domain mismatch: expected {expected_domain}, got {actual_domain}",
                )

    return VerifyResult(passed=True)


def verify_via_blind_critic(
    task_description: str,
    final_a11y_tree: str,
    *,
    run_id: str | None = None,
) -> CriticVerdict:
    """Terminal gate: independent Tier1 YES/NO on final state.

    Only called when ENABLE_BLIND_CRITIC=true and all L0 steps passed.
    """
    from shared_harness.llm_router import complete
    from shared_harness.prompt_loader import load_prompt

    prompt_text = load_prompt("blind_critic")
    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": f"TASK: {task_description}\n\nFINAL A11Y TREE:\n{final_a11y_tree}"},
    ]
    result = complete(
        tier=1,
        call_site="agent_blind_critic",
        messages=messages,
        schema=CriticVerdict,
        run_id=run_id,
        task_type="agent",
        max_tokens=1024,
    )
    return result  # type: ignore[return-value]


def blind_critic_enabled() -> bool:
    return os.environ.get("ENABLE_BLIND_CRITIC", "false").lower() in ("1", "true", "yes")
