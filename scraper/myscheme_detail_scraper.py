"""
Scrape detail pages for ALL collected scheme slugs.

Visits each myscheme.gov.in/schemes/{slug} page and extracts:
- Description, Benefits, Eligibility text, Application process, Documents

Saves checkpoints every 100 schemes so it can resume if interrupted.
"""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
SLUGS_PATH = os.path.join(OUTPUT_DIR, "all_slugs.json")
DETAILS_PATH = os.path.join(OUTPUT_DIR, "scheme_details_all.json")


async def main():
    with open(SLUGS_PATH, "r") as f:
        all_slugs = json.load(f)

    # Resume from checkpoint
    details = {}
    if os.path.exists(DETAILS_PATH):
        with open(DETAILS_PATH, "r", encoding="utf-8") as f:
            details = json.load(f)
        print(f"Resuming: {len(details)} already scraped")

    remaining = [s for s in all_slugs if s not in details]
    print(f"Total: {len(all_slugs)}, Remaining: {len(remaining)}")

    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        # Use 3 pages for parallel scraping
        pages = [await browser.new_page() for _ in range(3)]

        async def scrape_one(page, slug):
            url = f"https://www.myscheme.gov.in/schemes/{slug}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)

                body = await page.query_selector("body")
                text = await body.inner_text() if body else ""

                sections = {}
                current = "header"
                keys = ["details", "benefits", "eligibility", "application process", "documents required"]
                for line in text.split("\n"):
                    s = line.strip()
                    if s.lower() in keys:
                        current = s.lower()
                        continue
                    if s.lower() in ("frequently asked questions", "sources and references", "feedback", "was this helpful?"):
                        current = "skip"
                        continue
                    if current != "skip":
                        sections.setdefault(current, []).append(s)

                return {
                    "description": "\n".join(sections.get("details", [])[:15]).strip()[:1500],
                    "benefits": "\n".join(sections.get("benefits", [])[:15]).strip()[:1500],
                    "eligibility_text": "\n".join(sections.get("eligibility", [])[:15]).strip()[:1500],
                    "application_process": "\n".join(sections.get("application process", [])[:10]).strip()[:1000],
                    "documents": "\n".join(sections.get("documents required", [])[:10]).strip()[:1000],
                }
            except:
                return {"eligibility_text": "", "benefits": "", "description": ""}

        # Process in batches of 3 (parallel)
        for i in range(0, len(remaining), 3):
            batch = remaining[i:i+3]
            tasks = []
            for j, slug in enumerate(batch):
                pg = pages[j % len(pages)]
                tasks.append(scrape_one(pg, slug))

            results = await asyncio.gather(*tasks)
            for slug, result in zip(batch, results):
                details[slug] = result

            done = len(details)
            if done % 100 == 0 or done == len(all_slugs):
                elapsed = (time.time() - start) / 60
                rate = (done - (len(all_slugs) - len(remaining))) / max(elapsed, 0.01)
                eta = (len(remaining) - (i + len(batch))) / max(rate, 1)
                print(f"  [{done}/{len(all_slugs)}] {elapsed:.1f}min elapsed, ~{eta:.0f}min remaining")
                with open(DETAILS_PATH, "w", encoding="utf-8") as f:
                    json.dump(details, f, ensure_ascii=False)

            await asyncio.sleep(0.5)

        await browser.close()

    # Final save
    with open(DETAILS_PATH, "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2, ensure_ascii=False)

    elapsed = (time.time() - start) / 60
    has_elig = sum(1 for d in details.values() if d.get("eligibility_text", "").strip())
    print(f"\nDone! {len(details)} detail pages in {elapsed:.1f} min")
    print(f"With eligibility text: {has_elig}")


if __name__ == "__main__":
    asyncio.run(main())
