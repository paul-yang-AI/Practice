"""Playwright container smoke test — run locally or in Docker."""

from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--disable-dev-shm-usage", "--no-sandbox"],
            headless=True,
        )
        page = browser.new_page()
        page.goto("https://example.com", timeout=30000)
        title = page.title()
        browser.close()
    print(f"OK: Playwright smoke passed (title={title!r})")


if __name__ == "__main__":
    main()
