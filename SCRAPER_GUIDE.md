# Scraper Folder — Complete Guide

## Folder Structure

```
scraper/
├── __init__.py                  # Package marker
├── output/                      # Raw API/browser output files
│   ├── myscheme_full.json       # 1.5MB — First API scrape (4,585 schemes)
│   ├── myscheme_full_all.json   # 3.2MB — Merged dataset with details
│   ├── scheme_details.json      # 1.4MB — Eligibility text from detail pages
│   ├── scheme_listings.json     # 266KB — Intermediate listing data
│   ├── all_slugs.json           # 65KB — All scheme URL slugs
│   └── ... (intermediate files)
├── raw_data/                    # Large data files
│   ├── myscheme_ids.json        # 4.3MB — Full API response with all scheme IDs
│   ├── rescrape_results.json    # 840KB — Results from 6-sec-wait re-scrape
│   └── tier3_checkpoint.json    # 18KB — Checkpoint for Tier 3 enrichment
├── missing_criteria_slugs.json  # 512KB — Slugs of schemes needing criteria
│
│ ── CORE SCRIPTS (run in this order) ──
│
├── myscheme_id_collector.py     # Step 1: Token-steal + paginated API calls
│                                #   → Gets 4,585 scheme names/slugs/categories
│                                #   → Output: raw_data/myscheme_ids.json
│
├── myscheme_detail_scraper.py   # Step 2: Visit each detail page with Playwright
│                                #   → Extracts eligibility text, descriptions
│                                #   → Output: output/scheme_details.json
│
├── merger.py                    # Step 3: Merge API data + detail scrape data
│                                #   → Combines into single dataset
│                                #   → Output: output/myscheme_full_all.json
│
├── convert_to_seed.py           # Step 4: Parse eligibility text → structured criteria
│                                #   → Regex patterns for age/income/gender/caste
│                                #   → Used by reseed.py to populate DB
│
│ ── FIX/ENRICHMENT SCRIPTS ──
│
├── rescrape_eligibility.py      # Re-scraped 3,967 pages with 6 sec wait
│                                #   → Got 195 more eligibility texts
│
├── enrich_tier3.py              # Re-scraped 1,688 "Tier 3" pages
│                                #   → Used non-headless Chrome for better JS rendering
│                                #   → Got 136 more eligibility texts
│
├── generate_criteria_from_names.py  # Inferred criteria from scheme NAMES
│                                    #   → "Scholarship" → is_student=true
│                                    #   → "Mahila" → gender=female
│                                    #   → Added 2,550 criteria for 2,088 schemes
│
├── enrich_from_kaggle.py        # Used Kaggle CSV to fill gaps
│                                #   → Added descriptions for 2,602 schemes
│                                #   → Parsed 1,156 new criteria for 586 schemes
│                                #   → Added 201 new schemes not in our DB
│
│ ── DB MANAGEMENT SCRIPTS ──
│
├── get_missing_criteria.py      # Query DB for schemes with 0 criteria
├── insert_criteria.py           # Insert parsed criteria into DB
├── add_priority_schemes.py      # Add 10 manually verified priority schemes
├── add_baseline_criteria.py     # Add nationality=indian for empty schemes
├── add_state_criteria.py        # Copy state data to eligibility_criteria
├── fix_state_criteria.py        # Migrate scheme_states → eligibility_criteria
├── final_fixes.py               # Fix wrong criteria + add missing TN schemes
├── fix_db.py                    # ALTER TABLE to fix VARCHAR(300) limit
│
│ ── UTILITY SCRIPTS ──
│
├── check_data.py                # Full database audit — counts, quality checks
├── analyze_csv.py               # Analyze Kaggle CSV + cross-reference with DB
├── test_scrape.py               # Debug script to capture API request headers
├── myscheme_scraper.py          # Original Playwright scraper (v1, replaced)
└── data_gov_downloader.py       # data.gov.in downloader (not used — site needs login)
```

## How data flows

```
[MyScheme.gov.in API]
        │
        ▼
myscheme_id_collector.py ──→ raw_data/myscheme_ids.json (4,585 schemes)
        │
        ▼
myscheme_detail_scraper.py ──→ output/scheme_details.json (eligibility text)
        │
        ▼
merger.py ──→ output/myscheme_full_all.json (merged dataset)
        │
        ▼
convert_to_seed.py ──→ reseed.py ──→ PostgreSQL
        │
        ▼
[Enrichment scripts fill gaps]
  ├── rescrape_eligibility.py (6 sec wait re-scrape)
  ├── generate_criteria_from_names.py (name heuristics)
  ├── enrich_from_kaggle.py (Kaggle CSV cross-reference)
  └── final_fixes.py (manual verification fixes)
```
