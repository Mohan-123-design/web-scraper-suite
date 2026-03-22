import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import os
import json
import sys

SCRAPER_API_KEY = "e196351658e752f451849ccdd7a4d058"

BASE_URL = "https://www.homes.com/la-pine-or/"
PARAMS = "?ls-max=1000&ssit=Homes%20for%20sale%20in%20La%20Pine,%20OR,%20with%20lots%20up%20to%2010%20acres"

OUTPUT_FILE = "homes_la_pine_listings.xlsx"
PROGRESS_DIR = "progress"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

os.makedirs(PROGRESS_DIR, exist_ok=True)

# ---------------- PAGE-WISE PROGRESS ---------------- #

def progress_file(page):
    return os.path.join(PROGRESS_DIR, f"page_{page}.json")


def load_page_progress(page):
    file = progress_file(page)
    if os.path.exists(file):
        with open(file, "r") as f:
            return set(json.load(f)["scraped_urls"])
    return set()


def save_page_progress(page, scraped_urls):
    with open(progress_file(page), "w") as f:
        json.dump({
            "page": page,
            "scraped_urls": list(scraped_urls)
        }, f, indent=2)

# ---------------- FETCH PAGE ---------------- #

def fetch_page(url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            payload = {
                "api_key": SCRAPER_API_KEY,
                "url": url,
                "render": "true",
                "country_code": "us",
                "premium": "true"
            }

            r = requests.get(
                "https://api.scraperapi.com/",
                params=payload,
                headers=HEADERS,
                timeout=90
            )

            if r.status_code == 200 and len(r.text) > 5000:
                return r.text

            print(f"⚠️ Attempt {attempt}: status {r.status_code}")
            time.sleep(5)

        except Exception as e:
            print(f"❌ Attempt {attempt} failed:", e)
            time.sleep(5)

    return None

# ---------------- PARSING ---------------- #

def parse_listing_cards(html, source_page):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article")
    listings = []

    for card in cards:
        link = card.select_one("a[href]")
        if not link:
            continue

        listings.append({
            "Title": card.select_one("h3").get_text(strip=True) if card.select_one("h3") else None,
            "Price": card.find(string=lambda x: x and "$" in x),
            "Address": card.find("address").get_text(strip=True) if card.find("address") else None,
            "Source Item Link": "https://www.homes.com" + link["href"],
            "Source Page URL": source_page
        })

    return listings


def parse_detail_page(url):
    html = fetch_page(url)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    def safe(selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    details = {
        "Bedrooms": safe('[data-testid="beds"]'),
        "Bathrooms": safe('[data-testid="baths"]'),
        "Square Footage": safe('[data-testid="sqft"]'),
        "Listing Type": safe('[data-testid="listing-type"]'),
        "Realtor Name": safe('[data-testid="agent-name"]'),
        "Realtor Company": safe('[data-testid="broker-name"]'),
        "Property Details": soup.get_text(" ", strip=True)[:1200]
    }

    address = safe('[data-testid="address"]')
    if address and "," in address:
        parts = [p.strip() for p in address.split(",")]
        details["City"] = parts[-3] if len(parts) >= 3 else None
        state_zip = parts[-2].split()
        details["State"] = state_zip[0] if state_zip else None
        details["Zip"] = state_zip[-1] if state_zip else None

    return details

# ---------------- MAIN SCRAPER ---------------- #

def build_page_url(page):
    if page == 1:
        return f"{BASE_URL}{PARAMS}"
    return f"{BASE_URL}p{page}/{PARAMS}"


def scrape_all_pages(max_pages=6):
    if os.path.exists(OUTPUT_FILE):
        df = pd.read_excel(OUTPUT_FILE)
    else:
        df = pd.DataFrame()

    try:
        for page in range(1, max_pages + 1):
            page_url = build_page_url(page)
            print(f"\n🔍 Scraping page {page}: {page_url}")

            html = fetch_page(page_url)
            if not html:
                print("⚠️ Page fetch failed, stopping.")
                break

            listings = parse_listing_cards(html, page_url)
            print(f"📦 Listings found: {len(listings)}")

            if not listings:
                print("⚠️ No listings found, stopping.")
                break

            scraped_urls = load_page_progress(page)

            for item in listings:
                url = item["Source Item Link"]

                if url in scraped_urls:
                    print("⏭️ Already scraped")
                    continue

                print("➡️ Scraping:", url)
                item.update(parse_detail_page(url))

                df = pd.concat([df, pd.DataFrame([item])], ignore_index=True)
                df.to_excel(OUTPUT_FILE, index=False)

                scraped_urls.add(url)
                save_page_progress(page, scraped_urls)

                time.sleep(3)

            print(f"✅ Page {page} completed")
            time.sleep(6)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted safely")
        sys.exit(0)

    print("\n🎯 All pages scraped successfully")

if __name__ == "__main__":
    scrape_all_pages(max_pages=6)
