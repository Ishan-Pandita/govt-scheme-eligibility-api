"""
MyScheme.gov.in scraper using Playwright.

Extracts scheme name, ministry, description, eligibility criteria,
benefit details, and application links from MyScheme.gov.in.

Usage:
    python -m scraper.myscheme_scraper

Output:
    scraper/output/raw_schemes.json
"""

import asyncio
import json
import os
import time
from typing import Optional

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup


class MySchemesScraper:
    """Scrapes government schemes from MyScheme.gov.in."""

    BASE_URL = "https://www.myscheme.gov.in"
    SCHEMES_URL = f"{BASE_URL}/search"
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
    DELAY_BETWEEN_REQUESTS = 2  # seconds — be respectful

    def __init__(self):
        self.schemes: list[dict] = []
        self.browser: Optional[Browser] = None

    async def start(self, max_pages: int = 10, max_schemes: int = 100):
        """
        Main entry point. Scrapes scheme listings and detail pages.

        Args:
            max_pages: Maximum listing pages to scrape
            max_schemes: Maximum number of schemes to scrape details for
        """
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            page = await self.browser.new_page()

            # Step 1: Get scheme URLs from listing pages
            scheme_urls = await self._scrape_listing_pages(page, max_pages)
            print(f"Found {len(scheme_urls)} scheme URLs")

            # Step 2: Scrape each scheme's detail page
            for i, url in enumerate(scheme_urls[:max_schemes]):
                try:
                    print(f"[{i+1}/{min(len(scheme_urls), max_schemes)}] Scraping: {url}")
                    scheme_data = await self._scrape_scheme_detail(page, url)
                    if scheme_data:
                        self.schemes.append(scheme_data)
                    await asyncio.sleep(self.DELAY_BETWEEN_REQUESTS)
                except Exception as e:
                    print(f"  Error scraping {url}: {e}")
                    continue

            await self.browser.close()

        # Save results
        output_path = os.path.join(self.OUTPUT_DIR, "raw_schemes.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.schemes, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(self.schemes)} schemes to {output_path}")

    async def _scrape_listing_pages(self, page: Page, max_pages: int) -> list[str]:
        """Scrape scheme listing pages to collect scheme detail URLs."""
        urls = []

        for page_num in range(1, max_pages + 1):
            try:
                listing_url = f"{self.SCHEMES_URL}?page={page_num}"
                await page.goto(listing_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(self.DELAY_BETWEEN_REQUESTS)

                # Extract scheme links from listing
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                # MyScheme uses card-based layout with links
                links = soup.find_all("a", href=True)
                scheme_links = [
                    link["href"] for link in links
                    if "/scheme/" in link.get("href", "")
                ]

                if not scheme_links:
                    print(f"  No more schemes found on page {page_num}")
                    break

                for href in scheme_links:
                    full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    if full_url not in urls:
                        urls.append(full_url)

                print(f"  Page {page_num}: found {len(scheme_links)} scheme links")

            except Exception as e:
                print(f"  Error on listing page {page_num}: {e}")
                break

        return urls

    async def _scrape_scheme_detail(self, page: Page, url: str) -> Optional[dict]:
        """Scrape a single scheme detail page."""
        await page.goto(url, wait_until="networkidle", timeout=30000)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        # Extract scheme data
        name = self._extract_text(soup, "h1") or self._extract_text(soup, "h2")
        if not name:
            return None

        return {
            "name": name.strip(),
            "source_url": url,
            "description": self._extract_section(soup, "description"),
            "ministry": self._extract_section(soup, "ministry"),
            "eligibility": self._extract_section(soup, "eligibility"),
            "benefits": self._extract_section(soup, "benefits"),
            "application_process": self._extract_section(soup, "application process"),
            "documents_required": self._extract_section(soup, "documents required"),
        }

    def _extract_text(self, soup: BeautifulSoup, tag: str) -> Optional[str]:
        """Extract text from first matching tag."""
        element = soup.find(tag)
        return element.get_text(strip=True) if element else None

    def _extract_section(self, soup: BeautifulSoup, section_name: str) -> Optional[str]:
        """Extract content from a named section on the page."""
        # Try finding by heading text
        for heading in soup.find_all(["h2", "h3", "h4"]):
            if section_name.lower() in heading.get_text(strip=True).lower():
                # Get the next sibling content
                content_parts = []
                for sibling in heading.find_next_siblings():
                    if sibling.name in ["h2", "h3", "h4"]:
                        break
                    text = sibling.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                return " ".join(content_parts) if content_parts else None
        return None


async def main():
    """Run the scraper."""
    scraper = MySchemesScraper()
    await scraper.start(max_pages=5, max_schemes=50)


if __name__ == "__main__":
    asyncio.run(main())
