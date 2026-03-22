import pandas as pd
import requests
import time
import random
import os
from bs4 import BeautifulSoup

INPUT_FILE = "input2.xlsx"
OUTPUT_FILE = "outputrerun_1_600.xlsx"
RAW_DIR = "raw_pages1"
SCRAPER_API_KEY = "e196351658e752f451849ccdd7a4d058"

os.makedirs(RAW_DIR, exist_ok=True)

def log(msg):
    print(f"[INFO] {msg}")

def extract_home_type(html):
    soup = BeautifulSoup(html, "html.parser")

    for card in soup.select("div.home-facts-card"):
        title = card.select_one("p.home-facts-card-title")
        value = card.select_one("p.home-facts-card-text")

        if title and value and title.get_text(strip=True).lower() == "home type":
            return value.get_text(strip=True)

    return "Not Found"

def fetch_page(url):
    api_url = "https://api.scraperapi.com/"

    params = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
        "render": "true",
        "country_code": "us"
    }

    response = requests.get(api_url, params=params, timeout=120)
    response.raise_for_status()
    return response.text

def main():
    df = pd.read_excel(INPUT_FILE)
    link_col = [c for c in df.columns if "link" in c.lower()][0]

    if os.path.exists(OUTPUT_FILE):
        out_df = pd.read_excel(OUTPUT_FILE)
        processed = set(out_df["Row Number"])
        results = out_df.to_dict("records")
        log(f"Resuming. {len(processed)} rows already done.")
    else:
        processed = set()
        results = []

    for idx, row in df.iterrows():
        row_num = idx + 1
        if row_num in processed:
            continue

        url = str(row[link_col]).strip()
        log(f"Processing row {row_num}")

        try:
            html = fetch_page(url)

            raw_file = f"page_{row_num}.html"
            with open(os.path.join(RAW_DIR, raw_file), "w", encoding="utf-8") as f:
                f.write(html)

            home_type = extract_home_type(html)

            results.append({
                "Row Number": row_num,
                "Link": url,
                "Raw File": raw_file,
                "Home Type": home_type,
                "Status": "Success" if home_type != "Not Found" else "Home Type Not Found"
            })

            pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)
            log("Saved successfully")

        except Exception as e:
            log(f"Error: {e}")
            results.append({
                "Row Number": row_num,
                "Link": url,
                "Raw File": "",
                "Home Type": "",
                "Status": f"Error: {e}"
            })
            pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)

        time.sleep(random.uniform(2, 4))  # polite delay

    log("PROCESS COMPLETED")

if __name__ == "__main__":
    main()
