import pandas as pd
import requests
import time
import random
import os
import argparse
from bs4 import BeautifulSoup
from multiprocessing import Process

# ================= CONFIG ================= #

INPUT_FILE = "input.xlsx"
OUTPUT_DIR = "output_batches"
RAW_DIR = "raw_pages"

API_ENDPOINT = "https://api.webscrapingapi.com/v2"
API_KEY = "c7IhXewJTezo8lIyq6GXQmCAnN0gOwEZ"

MAX_RETRIES = 3
MIN_DELAY = 2
MAX_DELAY = 4

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================= UTILS ================= #

def log(msg):
    print(f"[INFO] {msg}", flush=True)

def is_valid_url(url):
    if not isinstance(url, str):
        return False
    url = url.strip()
    if not url or url.lower() == "nan":
        return False
    return url.startswith("http")

# ================= SCRAPER ================= #

def extract_home_type(html):
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.select("div.home-facts-card"):
        title = card.select_one("p.home-facts-card-title")
        value = card.select_one("p.home-facts-card-text")
        if title and value and title.get_text(strip=True).lower() == "home type":
            return value.get_text(strip=True)
    return "Not Found"

def fetch_page(url):
    if not is_valid_url(url):
        raise ValueError("Invalid URL")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            params = {
                "api_key": API_KEY,
                "url": url,
                "timeout": 90000,
                "country": "us",
                "render_js": "false"  # VERY IMPORTANT FOR HOMES.COM
            }

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

            r = requests.get(API_ENDPOINT, params=params, headers=headers, timeout=120)

            if r.status_code == 403:
                raise RuntimeError("PROVIDER_BLOCKED_403")

            if r.status_code == 200 and len(r.text) > 3000:
                return r.text

            log(f"Retry {attempt}/{MAX_RETRIES} | Status {r.status_code}")
            time.sleep(attempt * 2)

        except RuntimeError:
            raise

        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            log(f"Retry {attempt}/{MAX_RETRIES} | Error: {e}")
            time.sleep(attempt * 2)

    raise Exception("Fetch failed")

# ================= BATCH ================= #

def process_batch(start_row, end_row):
    df = pd.read_excel(INPUT_FILE)
    link_col = [c for c in df.columns if "link" in c.lower()][0]

    batch_file = f"{OUTPUT_DIR}/batch_{start_row}_{end_row}.xlsx"

    if os.path.exists(batch_file):
        out_df = pd.read_excel(batch_file)
        processed = set(out_df["Row Number"])
        results = out_df.to_dict("records")
        log(f"Resuming batch {start_row}-{end_row}")
    else:
        processed = set()
        results = []

    for idx in range(start_row - 1, min(end_row, len(df))):
        row_num = idx + 1
        if row_num in processed:
            continue

        url = df.iloc[idx][link_col]

        log(f"[Batch {start_row}-{end_row}] Row {row_num}")

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
                "Status": "Success"
            })

        except RuntimeError:
            results.append({
                "Row Number": row_num,
                "Link": url,
                "Raw File": "",
                "Home Type": "",
                "Status": "403 Blocked by Provider"
            })

        except Exception as e:
            results.append({
                "Row Number": row_num,
                "Link": url,
                "Raw File": "",
                "Home Type": "",
                "Status": f"Error: {e}"
            })

        pd.DataFrame(results).to_excel(batch_file, index=False)
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    log(f"Batch {start_row}-{end_row} completed")

# ================= MAIN ================= #

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()

    p = Process(target=process_batch, args=(args.start, args.end))
    p.start()
    p.join()
