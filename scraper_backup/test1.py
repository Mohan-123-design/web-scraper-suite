import pandas as pd
import time
import random
import os
import pyautogui
import pyperclip
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

INPUT_FILE = "input.xlsx"
OUTPUT_FILE = "output.xlsx"
RAW_DIR = "raw_pages"

os.makedirs(RAW_DIR, exist_ok=True)

def log(msg):
    print(f"[INFO] {msg}")

# ✅ CORRECT HOME TYPE PARSER (Homes.com)
def extract_home_type_from_text(html):
    try:
        soup = BeautifulSoup(html, "html.parser")

        cards = soup.find_all("div", class_="home-facts-card")
        for card in cards:
            title = card.find("p", class_="home-facts-card-title")
            value = card.find("p", class_="home-facts-card-text")

            if title and value:
                if title.get_text(strip=True).lower() == "home type":
                    return value.get_text(strip=True)

    except Exception as e:
        return f"Parse Error: {e}"

    return "Not Found"

# ✅ SAFE COPY WITH FALLBACK
def copy_page_content_safe(driver):
    for attempt in range(4):
        log(f"Copy attempt {attempt + 1}")

        driver.execute_script("window.focus();")
        time.sleep(2)

        # Trigger lazy load
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(1)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(2)

        content = pyperclip.paste()
        if content and len(content.strip()) > 500:
            log("Clipboard copy successful")
            return content

        log("Clipboard empty, retrying...")
        time.sleep(3)

    log("Clipboard failed, using page source fallback")
    return driver.page_source

def main():
    df = pd.read_excel(INPUT_FILE)

    link_cols = [c for c in df.columns if "link" in c.lower()]
    if not link_cols:
        raise Exception("No link column found in input.xlsx")

    link_col = link_cols[0]

    # ✅ Resume support
    if os.path.exists(OUTPUT_FILE):
        out_df = pd.read_excel(OUTPUT_FILE)
        processed_rows = set(out_df["Row Number"])
        results = out_df.to_dict("records")
        log(f"Resuming run. Already processed: {len(processed_rows)} rows")
    else:
        processed_rows = set()
        results = []

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(options=options)

    for idx, row in df.iterrows():
        row_num = idx + 1
        if row_num in processed_rows:
            continue

        link = str(row[link_col]).strip()
        log(f"Processing Row {row_num}: {link}")

        if not link.startswith("http"):
            results.append({
                "Row Number": row_num,
                "Link": link,
                "Raw File": "",
                "Home Type": "",
                "Status": "Invalid URL"
            })
            continue

        try:
            driver.get(link)
            log("Waiting for page to fully load")
            time.sleep(25)  # Homes.com needs this

            content = copy_page_content_safe(driver)

            raw_file = f"page_{row_num}.txt"
            raw_path = os.path.join(RAW_DIR, raw_file)

            with open(raw_path, "w", encoding="utf-8", errors="ignore") as f:
                f.write(content)

            home_type = extract_home_type_from_text(content)

            status = "Success" if home_type != "Not Found" else "Home Type Not Found"

            results.append({
                "Row Number": row_num,
                "Link": link,
                "Raw File": raw_file,
                "Home Type": home_type,
                "Status": status
            })

            pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)
            log("Row saved safely")

        except Exception as e:
            log(f"Handled error on row {row_num}: {e}")
            results.append({
                "Row Number": row_num,
                "Link": link,
                "Raw File": "",
                "Home Type": "",
                "Status": f"Error: {e}"
            })
            pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)

        time.sleep(random.uniform(5, 8))

    driver.quit()
    log("PROCESS COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    main()
