import csv
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

INPUT_CSV = "comreflink3.csv"
OUTPUT_CSV = "extracted_company_websites.csv"

# Selenium setup
chrome_options = Options()
chrome_options.add_argument("--headless")  # Comment this out if you want to see browser
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

driver = webdriver.Chrome(options=chrome_options)

def extract_website_url_selenium():
    # Try by link text (case-insensitive)
    try:
        links = driver.find_elements(By.XPATH, "//a[translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='visit website']")
        for a in links:
            href = a.get_attribute('href')
            if href and href.startswith("http"):
                return href
    except Exception:
        pass
    # Try by partial text or class/id match (StyledLink, etc.)
    try:
        links = driver.find_elements(By.XPATH, "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'visit website')]")
        for a in links:
            href = a.get_attribute('href')
            if href and href.startswith("http"):
                return href
    except Exception:
        pass
    try:
        links = driver.find_elements(By.XPATH, "//a[contains(@class, 'StyledLink') or contains(@class, 'link')]")
        for a in links:
            text = (a.text or "").strip().lower()
            href = a.get_attribute('href')
            if "visit website" in text and href and href.startswith("http"):
                return href
    except Exception:
        pass
    try:
        links = driver.find_elements(By.XPATH, "//a[contains(@id, 'visit')]")
        for a in links:
            href = a.get_attribute('href')
            if href and href.startswith("http"):
                return href
    except Exception:
        pass
    return ""

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Input file {INPUT_CSV} not found in the current directory.")
        return

    with open(INPUT_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        refcol = None
        for col in reader.fieldnames:
            if "reference" in col.lower() and "link" in col.lower():
                refcol = col
                break
        if not refcol:
            print("Error: Could not find reference link column in input CSV.")
            return
        inputrows = list(reader)
    
    results = []
    for idx, row in enumerate(inputrows, 1):
        reflink = row[refcol].strip()
        if not reflink.lower().startswith("http"):
            print(f"[{idx}/{len(inputrows)}] Skipping invalid link {reflink}")
            results.append({"Reference Link": reflink, "Website URL": "", "Status": "Invalid URL"})
            continue
        print(f"[{idx}/{len(inputrows)}] Visiting {reflink}")
        try:
            driver.get(reflink)
            # Give time for page to load and dynamic content to render
            time.sleep(4)
            url = extract_website_url_selenium()
            status = "Success" if url else "Website URL Not Found"
            results.append({"Reference Link": reflink, "Website URL": url, "Status": status})
        except Exception as e:
            print(f"[{idx}/{len(inputrows)}] Error processing {reflink}: {e}")
            results.append({"Reference Link": reflink, "Website URL": "", "Status": f"Error {e}"})
        time.sleep(1)  # polite delay

    driver.quit()
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["Reference Link", "Website URL", "Status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"Completed. Results saved to {OUTPUT_CSV}.")

if __name__ == "__main__":
    main()
