"""
data.gov.in dataset downloader and parser.

Downloads scheme-related CSV/JSON datasets from India's open data portal
and converts them into a structured format.

Usage:
    python -m scraper.data_gov_downloader

Output:
    scraper/output/datagov_schemes.json
"""

import csv
import json
import os
import io
from typing import Optional

import httpx


class DataGovDownloader:
    """Downloads and parses scheme data from data.gov.in."""

    BASE_URL = "https://data.gov.in"
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

    # Known dataset resource IDs for scheme data
    KNOWN_DATASETS = [
        {
            "name": "Central Government Schemes",
            "description": "List of central government welfare schemes",
            "url": "https://data.gov.in/resource/list-central-government-schemes",
        },
    ]

    def __init__(self):
        self.schemes: list[dict] = []

    async def download_and_parse(self):
        """Download datasets and parse into structured scheme data."""
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        async with httpx.AsyncClient(timeout=30.0) as client:
            for dataset in self.KNOWN_DATASETS:
                try:
                    print(f"Processing: {dataset['name']}")
                    # Note: data.gov.in requires API key for programmatic access
                    # This is a template — actual URLs need to be filled in
                    # after checking available datasets
                    print(f"  URL: {dataset['url']}")
                    print(f"  (Manual download may be required)")
                except Exception as e:
                    print(f"  Error: {e}")

        # Save whatever we collected
        output_path = os.path.join(self.OUTPUT_DIR, "datagov_schemes.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.schemes, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(self.schemes)} schemes to {output_path}")

    def parse_csv(self, csv_content: str) -> list[dict]:
        """Parse a CSV string into a list of scheme dictionaries."""
        schemes = []
        reader = csv.DictReader(io.StringIO(csv_content))

        for row in reader:
            scheme = {
                "name": row.get("Scheme Name", row.get("scheme_name", "")),
                "ministry": row.get("Ministry", row.get("ministry", "")),
                "description": row.get("Description", row.get("description", "")),
                "benefit_amount": row.get("Benefit", row.get("benefit", "")),
                "category": row.get("Category", row.get("category", "")),
            }
            if scheme["name"]:
                schemes.append(scheme)

        return schemes


if __name__ == "__main__":
    import asyncio
    downloader = DataGovDownloader()
    asyncio.run(downloader.download_and_parse())
