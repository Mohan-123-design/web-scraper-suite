import pandas as pd
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

INPUT_CSV = "comreflink4.csv"
OUTPUT_CSV = "extracted_company_websites.csv"

def extract_website_url(driver):
    # Try the "Visit website" button by text
    try:
        btn = driver.find_element(By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'visit website') and starts-with(@href, 'http')]")
        return btn.get_attribute("href")
    except NoSuchElementException:
        pass
    # Try anchor/button by known classes from reference logic
    class_selectors = [
        "//a[contains(@class,'website-btn')]",
        "//a[contains(@class,'hero__website-btn')]",
        "//a[contains(@class,'mat-button-base')]",
        "//a[contains(@class,'mat-flat-button')]",
        "//a[contains(@class,'mat-focus-indicator')]",
        "//a[@tabindex='0']"
    ]
    for selector in class_selectors:
        try:
            btn = driver.find_element(By.XPATH, selector)
            href = btn.get_attribute("href")
            if href and href.startswith("http"):
                return href
        except NoSuchElementException:
            continue
    # Fallback: find any anchor/button with 'website' in text and valid href
    try:
        anchors = driver.find_elements(By.XPATH, "//a[starts-with(@href, 'http')]")
        for a in anchors:
            text = a.text.lower()
            href = a.get_attribute("href")
            if "website" in text and all(excl not in href for excl in [
                "google.com", "linkedin.com", "facebook.com", "twitter.com", "docs.", "api.", "support.", "help.", "blog."
            ]):
                return href
    except Exception:
        pass
    return ""

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Input file {INPUT_CSV} not found.")
        return

    df = pd.read_csv(INPUT_CSV)
    ref_col = next((col for col in df.columns if "reference" in col.lower() and "link" in col.lower()), None)
    if not ref_col:
        print("Error: Could not find the reference link column in input CSV.")
        return

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # use normal mode for debugging
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)

    results = []
    for idx, row in df.iterrows():
        reference_link = str(row[ref_col]).strip()
        print(f"Processing [{idx+1}/{len(df)}]: {reference_link}")
        website_url = ""
        status = ""
        if not reference_link.lower().startswith("http"):
            results.append({"Reference Link": reference_link, "Company Website": "", "Status": "Invalid URL"})
            continue
        try:
            driver.get(reference_link)
            time.sleep(3)
            website_url = extract_website_url(driver)
            status = "Success" if website_url else "Website URL Not Found"
        except Exception as e:
            print(f"Error processing {reference_link}: {e}")
            status = f"Error: {e}"
            website_url = ""
        results.append({"Reference Link": reference_link, "Company Website": website_url, "Status": status})
        time.sleep(1)

    driver.quit()
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Completed. Results saved to {OUTPUT_CSV}.")

if __name__ == "__main__":
    main()
