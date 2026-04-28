"""
Step 2: Re-scrape detail pages for schemes missing eligibility criteria.
Uses 6 sec wait (vs 3 sec before) and 3 parallel tabs.
Saves checkpoints every 100 schemes.

Expected time: ~45 min for 3,967 pages.
"""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

MISSING_PATH = "scraper/missing_criteria_slugs.json"
RESULTS_PATH = "scraper/raw_data/rescrape_results.json"


def parse_sections(text):
    """Parse page body text into sections."""
    sections = {}
    current = "header"
    keys = ["details", "benefits", "eligibility", "application process", "documents required"]
    for line in text.split("\n"):
        s = line.strip()
        if s.lower() in keys:
            current = s.lower()
            continue
        if s.lower() in ("frequently asked questions", "sources and references",
                         "feedback", "was this helpful?", "share"):
            current = "skip"
            continue
        if current != "skip":
            sections.setdefault(current, []).append(s)
    return sections


async def main():
    with open(MISSING_PATH, "r", encoding="utf-8") as f:
        all_slugs = json.load(f)

    # Resume from checkpoint
    results = {}
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        for item in existing:
            results[item["slug"]] = item
        print(f"Resuming: {len(results)} already done")

    remaining = [s for s in all_slugs if s["slug"] not in results]
    print(f"Total missing: {len(all_slugs)}, Remaining: {len(remaining)}")

    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        pages = [await browser.new_page() for _ in range(3)]

        async def scrape_one(page, item):
            slug = item["slug"]
            db_id = item["db_id"]
            url = f"https://www.myscheme.gov.in/schemes/{slug}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(6000)  # KEY FIX: 6 sec instead of 3

                body = await page.query_selector("body")
                text = await body.inner_text() if body else ""
                sections = parse_sections(text)

                elig = "\n".join(sections.get("eligibility", [])[:20]).strip()[:2000]
                benefits = "\n".join(sections.get("benefits", [])[:15]).strip()[:1500]
                desc = "\n".join(sections.get("details", [])[:15]).strip()[:1500]

                return {
                    "db_id": db_id,
                    "slug": slug,
                    "eligibility_raw": elig,
                    "benefits_raw": benefits,
                    "description": desc,
                }
            except:
                return {"db_id": db_id, "slug": slug, "eligibility_raw": "", "benefits_raw": "", "description": ""}

        for i in range(0, len(remaining), 3):
            batch = remaining[i:i+3]
            tasks = [scrape_one(pages[j % 3], item) for j, item in enumerate(batch)]
            batch_results = await asyncio.gather(*tasks)

            for result in batch_results:
                results[result["slug"]] = result

            done = len(results)
            if done % 100 == 0 or i + 3 >= len(remaining):
                elapsed = (time.time() - start) / 60
                rate = (done - (len(all_slugs) - len(remaining))) / max(elapsed, 0.01)
                eta = (len(remaining) - (i + len(batch))) / max(rate, 1)

                has_elig = sum(1 for r in results.values() if r.get("eligibility_raw", "").strip())
                print(f"  [{done}/{len(all_slugs)}] {elapsed:.1f}m elapsed, ~{eta:.0f}m left | {has_elig} with eligibility")

                with open(RESULTS_PATH, "w", encoding="utf-8") as f:
                    json.dump(list(results.values()), f, ensure_ascii=False)

            await asyncio.sleep(0.5)

        await browser.close()

    # Final save
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(list(results.values()), f, indent=2, ensure_ascii=False)

    has_elig = sum(1 for r in results.values() if r.get("eligibility_raw", "").strip())
    print(f"\nDone! {len(results)} pages scraped, {has_elig} with eligibility text")


if __name__ == "__main__":
    asyncio.run(main())
