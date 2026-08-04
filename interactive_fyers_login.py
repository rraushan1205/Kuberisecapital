"""
Launch an interactive (headed) browser at the Fyers OAuth login page.

The user logs in manually (mobile + PIN + any OTP from their authenticator app).
This script just watches the browser until it redirects back to the local
callback (localhost:8000), then reports the resulting callback URL, page body,
and whether the broker connection was stored in the backend.
"""
import asyncio
import json
import sys
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright

AUTH_URL = sys.argv[1]
USER_EMAIL = sys.argv[2] if len(sys.argv) > 2 else "raushanraj1205@gmail.com"
USER_PASSWORD = sys.argv[3] if len(sys.argv) > 3 else "Raushan@1234"
API_BASE = "http://localhost:8000"


def is_localhost(url: str) -> bool:
    host = urlparse(url).hostname
    return host in ("localhost", "127.0.0.1")


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = await browser.new_context(viewport=None)
        page = await ctx.new_page()

        print("=" * 70)
        print("Interactive Fyers login launched.")
        print("Please complete the Fyers login in the browser window now.")
        print("Use: mobile 7488498589, PIN 3935, plus any OTP from your app.")
        print("=" * 70)
        print("Navigating to Fyers login...")
        await page.goto(AUTH_URL, wait_until="domcontentloaded", timeout=60000)
        print("Browser open at:", page.url)
        print("Waiting for you to log in and for redirect back to localhost...")

        for _ in range(180):  # up to 6 minutes
            await asyncio.sleep(2)
            try:
                url = page.url
            except Exception:
                # A navigation may be in progress; retry
                continue
            if is_localhost(url):
                print("\n>>> Detected redirect back to callback:", url)
                await asyncio.sleep(1)
                try:
                    body = await page.inner_text("body")
                except Exception as e:
                    body = f"(could not read body: {e})"
                print(">>> Callback page body:", body[:600])
                await page.screenshot(path="/tmp/fyers_callback.png")
                await browser.close()
                await check_backend()
                return

        print("Timed out waiting for callback. Last URL:", page.url)
        await page.screenshot(path="/tmp/fyers_timed_out.png")
        await browser.close()


async def check_backend() -> None:
    """Verify the broker connection was persisted by the backend."""
    print("\n--- Checking backend connection status ---")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": USER_EMAIL, "password": USER_PASSWORD},
        )
        if r.status_code != 200:
            print("Login failed:", r.status_code, r.text)
            return
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        sr = await client.get(f"{API_BASE}/api/v1/client/brokers/status", headers=headers)
        print("Broker status:", sr.status_code, json.dumps(sr.json(), indent=2))
        dr = await client.get(f"{API_BASE}/api/v1/client/dashboard", headers=headers)
        if dr.status_code == 200:
            data = dr.json()
            print("Dashboard broker field:", json.dumps(data.get("broker"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
