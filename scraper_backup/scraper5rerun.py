import pandas as pd
import requests
import time
import random
import os
import argparse
from bs4 import BeautifulSoup
from multiprocessing import Process

# ---------------- CONFIG ---------------- #

INPUT_FILE = "input2.xlsx"
OUTPUT_DIR = "output_batchesrerun"
RAW_DIR = "raw_pages3rerun"
SCRAPER_API_KEY = "13b3d72222e0c36ea56b6e29e2178a7a"

MAX_RETRIES = 3              # 🔴 capped
MIN_DELAY = 5
MAX_DELAY = 8

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- UTILS ---------------- #

def log(msg):
    print(f"[INFO] {msg}", flush=True)

def is_valid_url(url):
    return isinstance(url, str) and url.startswith("http")

# ---------------- SCRAPER ---------------- #

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

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            params = {
                "api_key": SCRAPER_API_KEY,
                "url": url,
                "country_code": "us",
                "timeout": 90,
                "render": "true" if attempt == 1 else "false"  # 🔑 render only once
            }

            r = requests.get(api_url, params=params, timeout=120)

            if r.status_code == 200 and len(r.text) > 3000:
                return r.text

            # 🔴 stop retrying 500 endlessly
            if r.status_code == 500:
                raise Exception("Blocked by site (500)")

            if r.status_code in (429, 502, 503):
                time.sleep(5 + random.uniform(1, 2))
                continue

            r.raise_for_status()

        except Exception as e:
            if "Blocked by site" in str(e):
                raise
            if attempt == MAX_RETRIES:
                raise
            time.sleep(5 + random.uniform(1, 2))

    raise Exception("Fetch failed")

# ---------------- BATCH WORKER ---------------- #

def process_batch(start_row, end_row):
    df = pd.read_excel(INPUT_FILE)
    link_col = [c for c in df.columns if "link" in c.lower()][0]

    batch_file = f"{OUTPUT_DIR}/batch_{start_row}_{end_row}.xlsx"

    if os.path.exists(batch_file):
        out_df = pd.read_excel(batch_file)
        processed = set(out_df["Row Number"])
        results = out_df.to_dict("records")
    else:
        processed = set()
        results = []

    for idx in range(start_row - 1, min(end_row, len(df))):
        row_num = idx + 1
        if row_num in processed:
            continue

        url = df.iloc[idx][link_col]

        if not is_valid_url(url):
            results.append({
                "Row Number": row_num,
                "Link": url,
                "Status": "Skipped: Invalid URL"
            })
            pd.DataFrame(results).to_excel(batch_file, index=False)
            continue

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
                "Status": "Success" if home_type != "Not Found" else "Home Type Not Found"
            })

        except Exception as e:
            status = "Blocked by site" if "Blocked" in str(e) else f"Error: {e}"
            results.append({
                "Row Number": row_num,
                "Link": url,
                "Status": status
            })

        pd.DataFrame(results).to_excel(batch_file, index=False)
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    log(f"Batch {start_row}-{end_row} completed")

# ---------------- MERGE ---------------- #

def merge_batches():
    files = [os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.endswith(".xlsx")]
    dfs = [pd.read_excel(f) for f in files]
    final = pd.concat(dfs).drop_duplicates("Row Number").sort_values("Row Number")
    final.to_excel("output.xlsx", index=False)
    log("Merged final output.xlsx")

# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--batch-index", type=int)
    parser.add_argument("--merge", action="store_true")
    args = parser.parse_args()

    if args.merge:
        merge_batches()
        exit()

    if args.start and args.end:
        p = Process(target=process_batch, args=(args.start, args.end))
        p.start()
        p.join()

    elif args.batch_size is not None and args.batch_index is not None:
        start = args.batch_index * args.batch_size + 1
        end = start + args.batch_size
        p = Process(target=process_batch, args=(start, end))
        p.start()
        p.join()

    else:
        print("Invalid arguments")
