"""One-shot private regression — pytest, smoke, SEC/Agent KPI, baseline JSON checks.

Fast (default, ~2–3 min):
  python scripts/run_private_regression.py

Full (+ Agent Playwright train/held-out, ~5–10 min, uses LLM):
  python scripts/run_private_regression.py --full

Refresh held-out JSON then verify:
  python scripts/run_private_regression.py --refresh-heldout

Writes reports/private_regression.json and exits 0/1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared_harness.env import load_env
from shared_harness.regression_checks import (
    verify_agent_heldout_summary,
    verify_agent_train_results,
    verify_sec_heldout_summary,
    verify_sec_train_results,
)

_REPORTS = _ROOT / "reports"
_SEC_HELDOUT = _REPORTS / "heldout_baseline.json"
_AGENT_HELDOUT = _REPORTS / "agent_heldout_baseline.json"


@dataclass
class StepResult:
    name: str
    ok: bool
    elapsed_s: float
    detail: str = ""


@dataclass
class RegressionReport:
    passed: bool
    mode: str
    steps: list[StepResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "mode": self.mode,
            "steps": [asdict(s) for s in self.steps],
        }


def _run_step(name: str, fn) -> StepResult:
    t0 = time.perf_counter()
    try:
        ok, detail = fn()
    except Exception as exc:
        ok, detail = False, str(exc)
    return StepResult(name=name, ok=ok, elapsed_s=round(time.perf_counter() - t0, 2), detail=detail)


def _run_subprocess(name: str, cmd: list[str]) -> StepResult:
    t0 = time.perf_counter()
    print(f"\n--- {name} ---")
    proc = subprocess.run(cmd, cwd=_ROOT, capture_output=False)
    elapsed = round(time.perf_counter() - t0, 2)
    ok = proc.returncode == 0
    detail = "exit 0" if ok else f"exit {proc.returncode}"
    return StepResult(name=name, ok=ok, elapsed_s=elapsed, detail=detail)


def _step_pytest() -> tuple[bool, str]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit",
        "tests/integration",
        "-q",
        "--tb=no",
    ]
    proc = subprocess.run(cmd, cwd=_ROOT, capture_output=True, text=True)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    summary = tail[-1] if tail else "no output"
    return proc.returncode == 0, summary


def _step_e2e_smoke() -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "e2e_smoke.py")],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    lines = (proc.stdout or "").splitlines()
    last = next((ln for ln in reversed(lines) if "All checks passed" in ln or "FAILED" in ln), "")
    return proc.returncode == 0, last or f"exit {proc.returncode}"


def _step_sec_train_eval() -> tuple[bool, str]:
    from shared_harness.eval_runner import run_sec_eval

    results = run_sec_eval(split="train", use_arbiter=False, use_llm_fallback=False)
    return verify_sec_train_results(results)


def _step_sec_heldout_json(refresh: bool) -> tuple[bool, str]:
    if refresh:
        proc = subprocess.run(
            [sys.executable, str(_ROOT / "scripts" / "run_heldout_baseline.py")],
            cwd=_ROOT,
        )
        if proc.returncode != 0:
            return False, "run_heldout_baseline.py failed"
    if not _SEC_HELDOUT.exists():
        return False, f"missing {_SEC_HELDOUT.name} (run scripts/run_heldout_baseline.py)"
    payload = json.loads(_SEC_HELDOUT.read_text(encoding="utf-8"))
    return verify_sec_heldout_summary(payload.get("summary", {}))


def _step_agent_train_eval() -> tuple[bool, str]:
    from shared_harness.eval_runner import run_agent_eval

    results = run_agent_eval(split="train")
    return verify_agent_train_results(results)


def _step_agent_heldout_json(refresh: bool) -> tuple[bool, str]:
    if refresh:
        proc = subprocess.run(
            [sys.executable, str(_ROOT / "scripts" / "run_agent_heldout_baseline.py")],
            cwd=_ROOT,
        )
        if proc.returncode != 0:
            return False, "run_agent_heldout_baseline.py failed"
    if not _AGENT_HELDOUT.exists():
        return False, f"missing {_AGENT_HELDOUT.name} (run scripts/run_agent_heldout_baseline.py)"
    payload = json.loads(_AGENT_HELDOUT.read_text(encoding="utf-8"))
    return verify_agent_heldout_summary(payload.get("summary", {}))


def _step_eval_manifest() -> tuple[bool, str]:
    """L3 eval tests (SEC + agent manifest depth)."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/eval/test_sec_manifest.py",
            "tests/eval/test_agent_tasks.py",
            "-q",
            "--tb=no",
        ],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    tail = (proc.stdout or "").strip().splitlines()
    return proc.returncode == 0, tail[-1] if tail else f"exit {proc.returncode}"


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Private regression harness")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include Agent Playwright train eval + L3 eval tests (slow, LLM cost)",
    )
    parser.add_argument(
        "--refresh-heldout",
        action="store_true",
        help="Re-run held-out baseline scripts before JSON checks",
    )
    parser.add_argument("--skip-pytest", action="store_true", help="Skip unit+integration pytest")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip e2e_smoke.py")
    parser.add_argument(
        "--skip-sec-train",
        action="store_true",
        help="Skip live SEC train eval (use if cache missing)",
    )
    args = parser.parse_args()

    mode = "full" if args.full else "fast"
    report = RegressionReport(passed=True, mode=mode)

    print("=" * 60)
    print(f"Private Regression ({mode})")
    print("=" * 60)

    if not args.skip_pytest:
        report.steps.append(_run_step("pytest_unit_integration", _step_pytest))

    if not args.skip_smoke:
        report.steps.append(_run_step("e2e_smoke", _step_e2e_smoke))

    if not args.skip_sec_train:
        report.steps.append(_run_step("sec_train_eval", _step_sec_train_eval))

    report.steps.append(
        _run_step(
            "sec_heldout_baseline",
            lambda: _step_sec_heldout_json(args.refresh_heldout),
        )
    )

    report.steps.append(
        _run_step(
            "agent_heldout_baseline_json",
            lambda: _step_agent_heldout_json(args.refresh_heldout and args.full),
        )
    )

    if args.full:
        report.steps.append(_run_step("agent_train_eval", _step_agent_train_eval))
        report.steps.append(_run_step("eval_manifest_l3", _step_eval_manifest))

    for step in report.steps:
        mark = "PASS" if step.ok else "FAIL"
        print(f"  [{mark}] {step.name} ({step.elapsed_s}s) — {step.detail}")
        if not step.ok:
            report.passed = False

    _REPORTS.mkdir(parents=True, exist_ok=True)
    out_path = _REPORTS / "private_regression.json"
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    print()
    print("=" * 60)
    if report.passed:
        print(f"All steps passed — wrote {out_path}")
    else:
        failed = [s.name for s in report.steps if not s.ok]
        print(f"FAILED steps: {', '.join(failed)}")
        print(f"Report: {out_path}")
    print("=" * 60)
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
