"""Playwright-based action executor for the agent loop."""

from __future__ import annotations

import logging
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright, TimeoutError as PwTimeout

from task1_agent.agent.dom_serialize import compress_a11y
from task1_agent.agent.loop import StepResult
from task1_agent.agent.recovery import FailureType, classify_failure
from task1_agent.agent.verify import VerifyResult, verify_step

logger = logging.getLogger(__name__)

_LAUNCH_ARGS = ["--disable-dev-shm-usage", "--no-sandbox"]
_DEFAULT_TIMEOUT = 15000


class PlaywrightExecutor:
    """Manages a single browser instance across multiple steps."""

    def __init__(self, *, headless: bool = True, timeout_ms: int = _DEFAULT_TIMEOUT):
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def start(self) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            args=_LAUNCH_ARGS,
            headless=self._headless,
        )
        self._context = self._browser.new_context()
        self._page = self._context.new_page()
        self._page.set_default_timeout(self._timeout_ms)

    def close(self) -> None:
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Executor not started")
        return self._page

    def __call__(self, action: str, context: dict) -> StepResult:
        """Execute an action and return a StepResult with verification."""
        step_index = context.get("step", 0)
        task = context.get("task", "")
        start_url = context.get("start_url", "")
        strategy = context.get("strategy")

        try:
            if action.startswith("recovery:"):
                return self._do_recovery(step_index, task, strategy or action)
            return self._do_navigate(step_index, task, start_url)
        except PwTimeout as exc:
            return StepResult(
                step_index=step_index,
                action=action,
                url=self.page.url,
                error=f"Timeout: {exc}",
                verify=VerifyResult(passed=False, reason=f"Timeout: {exc}"),
                failure_type=FailureType.TIMEOUT,
            )
        except Exception as exc:
            ft = classify_failure(str(exc))
            return StepResult(
                step_index=step_index,
                action=action,
                url=self.page.url if self._page else "",
                error=str(exc),
                verify=VerifyResult(passed=False, reason=str(exc)),
                failure_type=ft,
            )

    def _do_navigate(self, step_index: int, task: str, start_url: str) -> StepResult:
        """Navigate to start_url and observe page state."""
        page = self.page
        if step_index == 0 and start_url:
            page.goto(start_url, wait_until="domcontentloaded")
        else:
            page.wait_for_load_state("domcontentloaded")

        url = page.url
        title = page.title()
        body_text = page.inner_text("body")[:5000]
        a11y = self._get_a11y_snapshot()

        keywords = self._extract_keywords(task)
        vr = verify_step(
            url=url,
            page_text=f"{title}\n{body_text}",
            expected_keywords=keywords,
        )

        return StepResult(
            step_index=step_index,
            action=f"navigate:{start_url}" if step_index == 0 else "observe",
            url=url,
            page_text=body_text[:2000],
            a11y_tree=a11y,
            verify=vr,
            failure_type=classify_failure(vr.reason) if not vr.passed else None,
        )

    def _do_recovery(self, step_index: int, task: str, strategy: str) -> StepResult:
        """Apply a recovery strategy and re-observe."""
        page = self.page

        if "scroll" in strategy:
            page.evaluate("window.scrollBy(0, 500)")
        elif "navigate_back" in strategy:
            page.go_back()
        elif "press_enter" in strategy:
            page.keyboard.press("Enter")
        elif "click_parent" in strategy:
            page.evaluate("document.activeElement?.parentElement?.click()")
        elif "wait" in strategy or "extend" in strategy:
            page.wait_for_timeout(3000)
        else:
            page.wait_for_timeout(1000)

        page.wait_for_load_state("domcontentloaded")
        url = page.url
        title = page.title()
        body_text = page.inner_text("body")[:5000]
        a11y = self._get_a11y_snapshot()

        keywords = self._extract_keywords(task)
        vr = verify_step(
            url=url,
            page_text=f"{title}\n{body_text}",
            expected_keywords=keywords,
        )

        return StepResult(
            step_index=step_index,
            action=f"recovery:{strategy}",
            url=url,
            page_text=body_text[:2000],
            a11y_tree=a11y,
            verify=vr,
            failure_type=classify_failure(vr.reason) if not vr.passed else None,
        )

    def _get_a11y_snapshot(self) -> str:
        """Get compressed accessibility tree."""
        try:
            snapshot = self.page.accessibility.snapshot()
            return compress_a11y(snapshot or {}, max_chars=12000)
        except Exception:
            return compress_a11y(self.page.content()[:12000], max_chars=12000)

    def _extract_keywords(self, task: str) -> list[str]:
        """Extract simple verification keywords from task description."""
        keywords = []
        lower = task.lower()
        if "title" in lower and "example" in lower:
            keywords.append("Example Domain")
        elif "example.com" in lower:
            keywords.append("Example Domain")
        elif "httpbin" in lower and "header" in lower:
            keywords.append("headers")
        elif "wikipedia" in lower and "alan turing" in lower:
            keywords.append("Alan Turing")
        elif "hacker news" in lower:
            keywords.append("Hacker News")
        elif "duckduckgo" in lower:
            keywords.append("DuckDuckGo")
        elif "github" in lower and "cpython" in lower:
            keywords.append("cpython")
        return keywords
