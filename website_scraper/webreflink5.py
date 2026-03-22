import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

INPUT_FILE = 'comreflink5.csv'
OUTPUT_FILE = 'company_website_extracted.csv'
REFERENCE_COL_KEYWORDS = ['reference', 'link']

def find_reference_col(header_list):
    for col in header_list:
        if all(word in col.lower() for word in REFERENCE_COL_KEYWORDS):
            return col
    return None

def extract_website_from_page(driver):
    website_url = ''
    try:
        # Priority 1: <a> with class containing website-link
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[class*='website-link']")
        for a in anchors:
            href = a.get_attribute('href')
            if href and href.startswith('http') and 'documentation' not in href.lower():
                return href

        # Priority 2: <a> tags with visible text containing 'website'
        anchors = driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'WEBSITE', 'website'), 'website')]")
        for a in anchors:
            href = a.get_attribute('href')
            if href and href.startswith('http') and 'documentation' not in href.lower():
                return href

        # Priority 3: Any <a> with text 'website' not excluded
        exclude_domains = ['docs.', 'api.', 'developer.', 'support.', 'help.', 'linkedin.com',
                           'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 'github.com']
        anchors = driver.find_elements(By.TAG_NAME, 'a')
        for a in anchors:
            text = a.text.lower()
            href = a.get_attribute('href')
            if 'website' in text and href and href.startswith('http') and not any(ex in href for ex in exclude_domains):
                return href
    except Exception as e:
        pass
    return website_url

def main():
    df = pd.read_csv(INPUT_FILE)
    ref_col = find_reference_col(df.columns)
    if not ref_col:
        print("Error: Could not find reference link column!")
        return

    options = Options()
    options.add_argument("--headless") # Runs Chrome in headless mode.
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    driver = webdriver.Chrome(options=options)

    results = []
    for idx, row in df.iterrows():
        ref_link = str(row[ref_col]).strip()
        print(f'Processing {idx+1}/{len(df)}: {ref_link}')
        if not ref_link.startswith('http'):
            results.append({'Reference Link': ref_link, 'Website URL': '', 'Status': 'Invalid URL'})
            continue

        try:
            driver.get(ref_link)
            time.sleep(3) # Wait for JS-rendered content
            website_url = extract_website_from_page(driver)
            status = 'Success' if website_url else 'Website Not Found'
            results.append({'Reference Link': ref_link, 'Website URL': website_url, 'Status': status})
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            results.append({'Reference Link': ref_link, 'Website URL': '', 'Status': f'Error: {e}'})
        time.sleep(1)  # Respectful crawl

    driver.quit()
    pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)
    print(f"Extraction complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
