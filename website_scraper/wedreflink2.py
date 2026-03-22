import os
import csv
import time
import requests
from bs4 import BeautifulSoup

INPUT_FILE = "comreflink2.csv"
OUTPUT_FILE = "extracted_company_websites.csv"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

def extract_website_from_soup(soup):
    # Generic extraction for "Visit website" (green-circled in your image)
    candidates = []
    # Find all <a> tags that have "Visit website" or similar in their text
    for a_tag in soup.find_all("a", href=True):
        text = a_tag.get_text(strip=True).lower()
        if "visit website" in text or "website" in text:
            candidates.append(a_tag['href'])
    if candidates:
        return candidates[0]  # Take the first matching link
    # Fallback: look for button tags or other obvious CTAs
    for btn in soup.find_all(["a", "button"], href=True):
        btn_text = btn.get_text(strip=True).lower()
        if "website" in btn_text:
            return btn['href']
    return ""

def find_reference_column(fieldnames):
    # Return the name of the column containing both "reference" and "link" (case-insensitive)
    for col in fieldnames:
        if "reference" in col.lower() and "link" in col.lower():
            return col
    for col in fieldnames:
        if "link" in col.lower():
            return col
    return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file '{INPUT_FILE}' not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8', newline='') as infile:
        reader = csv.DictReader(infile)
        ref_col = find_reference_column(reader.fieldnames)
        if not ref_col:
            print("Error: Could not find reference link column in input CSV.")
            return
        rows = list(reader)

    results = []
    for idx, row in enumerate(rows, 1):
        url = row[ref_col].strip()
        print(f"[{idx}/{len(rows)}] Processing: {url}")
        if not url.lower().startswith("http"):
            results.append({"Reference Link": url, "Scraped Website": "", "Status": "Invalid URL"})
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            website_url = extract_website_from_soup(soup)
            status = "Success" if website_url else "Not Found"
            results.append({
                "Reference Link": url,
                "Scraped Website": website_url,
                "Status": status
            })
        except Exception as e:
            results.append({"Reference Link": url, "Scraped Website": "", "Status": f"Error: {str(e)}"})
        time.sleep(1)  # Be polite

    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=["Reference Link", "Scraped Website", "Status"])
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"Completed. Results saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
