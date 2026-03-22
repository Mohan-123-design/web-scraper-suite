import pandas as pd
import requests
import time
import random
import os
import argparse
from bs4 import BeautifulSoup
from multiprocessing import Process

INPUT_FILE = "input.xlsx"
OUTPUT_DIR = "output_batches"
RAW_DIR = "raw_pages"
SCRAPER_API_KEY = "c7IhXewJTezo8lIyq6GXQmCAnN0gOwEZ"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def log(msg):
    print(f"[INFO] {msg}", flush=True)

# ---------------- SCRAPER LOGIC ---------------- #

def extract_home_type(html):
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.select("div.home-facts-card"):
        title = card.select_one("p.home-facts-card-title")
        value = card.select_one("p.home-facts-card-text")
        if title and value and title.get_text(strip=True).lower() == "home type":
            return value.get_text(strip=True)
    return "Not Found"

def fetch_page(url):
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
        "render": "true",
        "country_code": "us"
    }
    r = requests.get("https://api.scraperapi.com/", params=params, timeout=120)
    r.raise_for_status()
    return r.text

# ---------------- BATCH WORKER ---------------- #

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

        url = str(df.iloc[idx][link_col]).strip()
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
            results.append({
                "Row Number": row_num,
                "Link": url,
                "Raw File": "",
                "Home Type": "",
                "Status": f"Error: {e}"
            })

        pd.DataFrame(results).to_excel(batch_file, index=False)
        time.sleep(random.uniform(2, 4))

    log(f"Batch {start_row}-{end_row} completed")

# ---------------- MERGE OUTPUT ---------------- #

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
