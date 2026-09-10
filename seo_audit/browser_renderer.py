"""
Browser Renderer component providing headless Chromium rendering fallback for JavaScript-rendered SPAs.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BrowserRenderer:
    """Headless browser rendering engine for dynamic Single Page Applications (SPAs)."""

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent
        self._playwright = None
        self._browser = None
        self._is_initialized = False
        self._available = True

    def _ensure_browser(self) -> bool:
        """Lazily initialize Playwright and launch Chromium headless browser."""
        if self._is_initialized and self._browser:
            return True

        if not self._available:
            return False

        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            self._is_initialized = True
            logger.info("Headless Chromium browser initialized for hybrid SPA rendering.")
            return True
        except Exception as e:
            logger.warning(f"Could not launch Playwright browser: {e}. Falling back to standard HTTP HTML.")
            self._available = False
            return False

    def render_page(self, url: str, timeout: float = 15.0) -> Optional[str]:
        """
        Navigate to URL in headless Chromium, wait for JavaScript execution and hydration,
        and return the fully rendered DOM HTML string.
        """
        if not self._ensure_browser():
            return None

        page = None
        try:
            context = self._browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Navigate with networkidle or domcontentloaded
            try:
                page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            except Exception:
                # Fallback to domcontentloaded with short hydration delay
                page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))

            # Small grace period for React/Vue client-side hydration
            page.wait_for_timeout(1500)

            rendered_html = page.content()
            context.close()
            return rendered_html
        except Exception as e:
            logger.warning(f"Browser rendering failed for {url}: {e}")
            if page:
                try:
                    page.context.close()
                except Exception:
                    pass
            return None

    def close(self) -> None:
        """Clean up browser and playwright instances."""
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        self._is_initialized = False
