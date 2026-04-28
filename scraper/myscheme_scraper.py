"""
MyScheme.gov.in full pipeline scraper.

Phase 1: Collect scheme slugs by typing keywords in search box
         (triggers API calls we intercept — avoids pagination issue)
Phase 2: Visit each detail page, extract eligibility text
Phase 3: Save everything for AI structuring

Usage: python -m scraper.myscheme_scraper
"""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# Keywords to search — each triggers a different API response
KEYWORDS = [
    "", "pension", "scholarship", "insurance", "loan", "housing", "health",
    "education", "agriculture", "women", "disability", "skill", "employment",
    "subsidy", "child", "marriage", "maternity", "widow", "farmer",
    "student", "minority", "tribal", "labour", "worker", "training",
    "entrepreneur", "pradhan mantri", "national", "youth", "senior",
    "food", "water", "sanitation", "energy", "solar", "electric",
    "transport", "road", "rural", "urban", "digital", "internet",
    "bank", "credit", "savings", "ration", "BPL", "APL",
    "SC", "ST", "OBC", "EWS", "transgender", "orphan",
    "fisherman", "weaver", "artisan", "handicraft", "textile",
    "sports", "culture", "research", "fellowship", "PhD",
    "startup", "MSME", "industry", "export", "trade",
    "medical", "hospital", "surgery", "cancer", "kidney",
    "marriage assistance", "death benefit", "accident", "funeral",
    "bicycle", "laptop", "uniform", "books", "hostel",
    "coaching", "competitive exam", "IAS", "engineering",
    "law", "pharmacy", "nursing", "teacher", "professor",
    "police", "army", "navy", "air force", "defence",
    "construction worker", "domestic worker", "driver", "vendor",
    "dairy", "poultry", "fisheries", "sericulture", "horticulture",
    "irrigation", "drip", "greenhouse", "cold storage",
    "toilet", "gas connection", "LPG", "electricity",
    "drinking water", "well", "borewell", "tank",
    "flood", "drought", "disaster", "relief", "compensation",
    "land", "plot", "house", "flat", "rent",
    "pension scheme", "old age", "destitute", "beggar",
    "HIV", "AIDS", "TB", "leprosy", "mental health",
    "eye", "hearing", "prosthetic", "wheelchair",
    "Gujarat", "Maharashtra", "Tamil Nadu", "Karnataka", "Kerala",
    "Rajasthan", "Bihar", "UP", "MP", "Odisha",
    "West Bengal", "Assam", "Punjab", "Haryana", "Jharkhand",
    "Chhattisgarh", "Uttarakhand", "HP", "Goa", "Sikkim",
    "Tripura", "Meghalaya", "Mizoram", "Nagaland", "Manipur",
    "Arunachal", "Delhi", "Puducherry", "Jammu", "Ladakh",
    "Telangana", "Andhra Pradesh",
]

all_items = {}  # slug -> item data


async def phase1_collect_slugs():
    """Type keywords into search box, intercept API responses to collect slugs."""
    print("=" * 60)
    print("  PHASE 1: Collecting scheme slugs via keyword search")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})

        async def on_response(response):
            if "search/v6/schemes" in response.url and response.status == 200:
                try:
                    body = await response.json()
                    items = body.get("data", {}).get("hits", {}).get("items", [])
                    for item in items:
                        fields = item.get("fields", {})
                        slug = fields.get("slug", "")
                        if slug and slug not in all_items:
                            all_items[slug] = {
                                "name": fields.get("schemeName", ""),
                                "slug": slug,
                                "ministry": fields.get("nodalMinistryName", ""),
                                "description": fields.get("briefDescription", "")[:500],
                                "scheme_type": "central" if fields.get("level", "").lower() == "central" else "state",
                                "category": ", ".join(fields.get("schemeCategory", [])) if isinstance(fields.get("schemeCategory"), list) else "",
                                "states": [s for s in fields.get("beneficiaryState", []) if s != "All"] if isinstance(fields.get("beneficiaryState"), list) else [],
                            }
                except:
                    pass

        page.on("response", on_response)

        # Load initial page
        await page.goto("https://www.myscheme.gov.in/search", wait_until="networkidle")
        await page.wait_for_timeout(8000)
        print(f"  Initial load: {len(all_items)} unique schemes")

        # Find search box and type keywords
        search_box = page.locator('input[type="search"], input[placeholder*="Search"], input[placeholder*="search"]')
        if await search_box.count() == 0:
            search_box = page.locator('input').first

        for i, kw in enumerate(KEYWORDS):
            try:
                await search_box.click()
                await search_box.fill("")
                await search_box.fill(kw)
                await search_box.press("Enter")
                await page.wait_for_timeout(3000)

                if (i + 1) % 10 == 0:
                    print(f"  Keyword {i+1}/{len(KEYWORDS)}: '{kw}' → {len(all_items)} unique schemes")
            except Exception as e:
                print(f"  Keyword '{kw}' error: {e}")

            if len(all_items) >= 500:
                print(f"  Reached 500+ schemes!")
                break

        await browser.close()

    # Save slugs
    slug_path = os.path.join(OUTPUT_DIR, "scheme_slugs.json")
    with open(slug_path, "w", encoding="utf-8") as f:
        json.dump(list(all_items.keys()), f, indent=2)

    listing_path = os.path.join(OUTPUT_DIR, "scheme_listings.json")
    with open(listing_path, "w", encoding="utf-8") as f:
        json.dump(list(all_items.values()), f, indent=2, ensure_ascii=False)

    print(f"\n  Phase 1 complete: {len(all_items)} unique schemes")
    print(f"  Saved to: {listing_path}")
    return list(all_items.keys())


async def phase2_scrape_details(slugs):
    """Visit each detail page and extract eligibility text."""
    print("\n" + "=" * 60)
    print(f"  PHASE 2: Scraping {len(slugs)} detail pages")
    print("=" * 60)

    details = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page()

        for i, slug in enumerate(slugs):
            url = f"https://www.myscheme.gov.in/schemes/{slug}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(5000)

                body = await page.query_selector("body")
                text = await body.inner_text() if body else ""

                # Parse sections
                sections = {}
                current = "header"
                section_keys = ["details", "benefits", "eligibility", "application process", "documents required"]
                for line in text.split("\n"):
                    s = line.strip()
                    if s.lower() in section_keys:
                        current = s.lower()
                        continue
                    if s.lower() in ("frequently asked questions", "sources and references", "feedback", "was this helpful?"):
                        current = "skip"
                        continue
                    if current != "skip":
                        sections.setdefault(current, []).append(s)

                details[slug] = {
                    "description": "\n".join(sections.get("details", [])[:15]).strip()[:1500],
                    "benefits": "\n".join(sections.get("benefits", [])[:15]).strip()[:1500],
                    "eligibility_text": "\n".join(sections.get("eligibility", [])[:15]).strip()[:1500],
                    "application_process": "\n".join(sections.get("application process", [])[:10]).strip()[:1000],
                    "documents": "\n".join(sections.get("documents required", [])[:10]).strip()[:1000],
                }

                if (i + 1) % 25 == 0:
                    print(f"  [{i+1}/{len(slugs)}] {slug} — elig: {len(details[slug]['eligibility_text'])} chars")
                    # Save checkpoint
                    with open(os.path.join(OUTPUT_DIR, "scheme_details.json"), "w", encoding="utf-8") as f:
                        json.dump(details, f, indent=2, ensure_ascii=False)

            except Exception as e:
                print(f"  [{i+1}/{len(slugs)}] {slug} ERROR: {e}")

            await asyncio.sleep(1)

        await browser.close()

    # Final save
    detail_path = os.path.join(OUTPUT_DIR, "scheme_details.json")
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2, ensure_ascii=False)

    print(f"\n  Phase 2 complete: {len(details)} detail pages scraped")
    return details


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start = time.time()

    # Phase 1: Collect slugs
    slugs = await phase1_collect_slugs()

    # Phase 2: Scrape details
    details = await phase2_scrape_details(slugs)

    # Merge listings + details
    listing_path = os.path.join(OUTPUT_DIR, "scheme_listings.json")
    listings = json.load(open(listing_path, "r", encoding="utf-8"))

    merged = []
    for listing in listings:
        slug = listing["slug"]
        detail = details.get(slug, {})
        merged.append({**listing, **detail})

    out = os.path.join(OUTPUT_DIR, "myscheme_full.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    elapsed = (time.time() - start) / 60
    print(f"\n{'='*60}")
    print(f"  DONE! {len(merged)} schemes with eligibility data")
    print(f"  Time: {elapsed:.1f} minutes")
    print(f"  Output: {out}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
