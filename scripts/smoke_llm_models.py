"""Optional LLM model ID smoke — requires API keys."""

from __future__ import annotations

import os
import sys


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        print("SKIP: no GEMINI_API_KEY / GOOGLE_API_KEY")
        sys.exit(0)
    try:
        import litellm

        model = os.environ.get("LLM_TIER1_PRIMARY", "gemini/gemini-2.0-flash")
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "Reply with JSON: {\"ok\": true}"}],
            max_tokens=32,
        )
        print(f"OK: {model} -> {resp.choices[0].message.content[:80]}")
    except Exception as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
