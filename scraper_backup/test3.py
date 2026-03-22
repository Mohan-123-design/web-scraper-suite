import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import os
import json
import sys

SCRAPER_API_KEY = "ea664af66a8b5ce02eb4bff0371ad51d"

BASE_URL = "https://www.homes.com/la-pine-or/"
PARAMS = "?ls-max=1000&ssit=Homes%20for%20sale%20in%20La%20Pine,%20OR,%20with%20lots%20up%20to%2010%20acres"

OUTPUT_FILE = "homes_la_pine_listings.xlsx"
PROGRESS_FILE = "progress.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ---------------- LOAD / SAVE PROGRESS ---------------- #

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"page": 1, "scraped_urls": []}


def save_progress(page, scraped_urls):
    with open(PROGRESS_FILE, "w") as f:
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

        detail_url = "https://www.homes.com" + link["href"]

        title = card.select_one("h3")
        price = card.find(string=lambda x: x and "$" in x)
        address = card.find("address")

        listings.append({
            "Title": title.get_text(strip=True) if title else None,
            "Price": price.strip() if price else None,
            "Address": address.get_text(strip=True) if address else None,
            "Source Item Link": detail_url,
            "Source Page URL": source_page
        })

    return listings


def parse_detail_page(url):
    html = fetch_page(url)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    def safe_text(selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    details = {
        "Bedrooms": safe_text('[data-testid="beds"]'),
        "Bathrooms": safe_text('[data-testid="baths"]'),
        "Square Footage": safe_text('[data-testid="sqft"]'),
        "Listing Type": safe_text('[data-testid="listing-type"]'),
        "Realtor Name": safe_text('[data-testid="agent-name"]'),
        "Realtor Company": safe_text('[data-testid="broker-name"]'),
        "Property Details": soup.get_text(" ", strip=True)[:1200]
    }

    address = safe_text('[data-testid="address"]')
    if address and "," in address:
        parts = [p.strip() for p in address.split(",")]
        details["City"] = parts[-3] if len(parts) >= 3 else None
        state_zip = parts[-2].split()
        details["State"] = state_zip[0] if state_zip else None
        details["Zip"] = state_zip[-1] if state_zip else None

    return details

# ---------------- MAIN SCRAPER ---------------- #

def scrape_all_pages():
    progress = load_progress()
    start_page = progress["page"]
    scraped_urls = set(progress["scraped_urls"])

    if os.path.exists(OUTPUT_FILE):
        df_existing = pd.read_excel(OUTPUT_FILE)
    else:
        df_existing = pd.DataFrame()

    page = start_page

    try:
        while True:
            page_url = f"{BASE_URL}{PARAMS}&page={page}"
            print(f"\n🔍 Scraping page {page}")

            html = fetch_page(page_url)
            if not html:
                break

            listings = parse_listing_cards(html, page_url)
            if not listings:
                break

            for item in listings:
                detail_url = item["Source Item Link"]

                if detail_url in scraped_urls:
                    print("⏭️ Skipping already scraped")
                    continue

                print("➡️ Scraping:", detail_url)
                details = parse_detail_page(detail_url)
                item.update(details)

                df_existing = pd.concat(
                    [df_existing, pd.DataFrame([item])],
                    ignore_index=True
                )

                df_existing.to_excel(OUTPUT_FILE, index=False)

                scraped_urls.add(detail_url)
                save_progress(page, scraped_urls)

                time.sleep(3)

            page += 1
            save_progress(page, scraped_urls)
            time.sleep(6)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted safely. Progress saved.")
        sys.exit(0)

    print("\n✅ Scraping completed fully.")


if __name__ == "__main__":
    scrape_all_pages()
