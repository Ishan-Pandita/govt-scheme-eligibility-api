"""Debug: capture ALL request headers to the API."""
import asyncio
import json
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        page = await browser.new_page()

        async def handle_request(request):
            if "api.myscheme.gov.in" in request.url:
                print(f"\nREQUEST to: {request.url[:80]}")
                print(f"Method: {request.method}")
                headers = request.headers
                for k, v in sorted(headers.items()):
                    print(f"  {k}: {v[:100]}")

        page.on("request", handle_request)

        await page.goto("https://www.myscheme.gov.in/search")
        await page.wait_for_timeout(12000)
        await browser.close()

asyncio.run(debug())
