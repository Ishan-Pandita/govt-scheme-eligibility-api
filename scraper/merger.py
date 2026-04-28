"""
Merge all data sources into final dataset.

1. scheme_listings_full.json (4,585 schemes with basic info from API)
2. scheme_details_all.json (detail pages - some have eligibility)
3. scheme_details.json (504 schemes with good eligibility from earlier scrape)
"""
import json
import os

OUTPUT_DIR = os.path.join("scraper", "output")

def main():
    # Load all sources
    listings = json.load(open(os.path.join(OUTPUT_DIR, "scheme_listings_full.json"), "r", encoding="utf-8"))
    details_all = json.load(open(os.path.join(OUTPUT_DIR, "scheme_details_all.json"), "r", encoding="utf-8"))
    
    # Earlier 504 with good eligibility
    details_504 = {}
    old_path = os.path.join(OUTPUT_DIR, "scheme_details.json")
    if os.path.exists(old_path):
        details_504 = json.load(open(old_path, "r", encoding="utf-8"))

    print(f"Listings: {len(listings)}")
    print(f"Details (all): {len(details_all)}")
    print(f"Details (504 good): {len(details_504)}")

    # Merge: prefer the 504 good details, fall back to all details
    merged = []
    for listing in listings:
        slug = listing["slug"]
        
        # Try good details first
        detail = details_504.get(slug, {})
        if not detail.get("eligibility_text", "").strip():
            detail = details_all.get(slug, {})
        
        merged.append({**listing, **detail})

    # Stats
    has_elig = sum(1 for m in merged if m.get("eligibility_text", "").strip())
    has_desc = sum(1 for m in merged if m.get("description", "").strip())
    has_benefits = sum(1 for m in merged if m.get("benefits", "").strip())

    print(f"\nMerged: {len(merged)} schemes")
    print(f"  With eligibility: {has_elig}")
    print(f"  With description: {has_desc}")
    print(f"  With benefits: {has_benefits}")

    # Save
    out = os.path.join(OUTPUT_DIR, "myscheme_full_all.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: {out}")

if __name__ == "__main__":
    main()
