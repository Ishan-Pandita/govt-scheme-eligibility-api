"""Navigate directly to the aistore iframe URL to bypass cross-origin restriction."""
import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Go directly to the iframe URL
        await page.goto("https://aistore.myscheme.in/6t4rIofAaIAEgu2P9lmtD?isEmbed=true", wait_until="networkidle")
        await page.wait_for_timeout(10000)
        
        # Scroll to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)
        
        # Check for pagination
        result = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('*');
                const results = [];
                for (const el of els) {
                    const cls = (el.className || '').toString();
                    if (cls.includes('pagination') || cls.includes('Pagination') || cls.includes('page')) {
                        results.push({
                            tag: el.tagName, class: cls.substring(0, 100),
                            text: (el.innerText || '').substring(0, 80),
                        });
                    }
                }
                return results;
            }
        """)
        print(f"Pagination elements: {len(result)}")
        for r in result[:20]:
            print(f"  <{r['tag']}> class='{r['class']}' text='{r['text']}'")

        # Get page text to see what loaded
        body = await page.query_selector("body")
        text = await body.inner_text() if body else ""
        print(f"\nPage text (first 500 chars):\n{text[:500]}")

        await page.wait_for_timeout(2000)
        await browser.close()

asyncio.run(debug())
