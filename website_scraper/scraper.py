import time
import os
import csv
import logging
import random
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SEARCH_URL = "https://www.upwork.com/nx/search/jobs/?amount=50-&hourly_rate=5-50&location=Australia%2520and%2520New%2520Zealand,Central%2520America,Northern%2520America,South%2520America,Australia,Canada,France,Germany,Netherlands,United%2520Arab%2520Emirates,United%2520Kingdom,United%2520States&nbs=1&per_page=20&q=B2b%20lead%20generation&sort=recency&t=0,1&page=1"
CSV_FILE = "upwork_job_structured_details.csv"
TXT_DIR = "job_texts"
os.makedirs(TXT_DIR, exist_ok=True)

def collect_job_links(driver, wait):
    driver.get(SEARCH_URL)
    try:
        cookie_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-qa='cookie-banner-accept']"))
        )
        cookie_btn.click()
        logging.info("Cookie consent accepted")
    except TimeoutException:
        logging.info("No cookie consent popup found")
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))
    job_link_elements = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='/jobs/']"))
    )
    links = []
    for elem in job_link_elements:
        href = elem.get_attribute("href")
        if href and "/jobs/" in href and href not in links and "~" in href:
            links.append(href)
    logging.info(f"Found {len(links)} job links")
    return links

def save_job_text(driver, url, idx):
    driver.get(url)
    time.sleep(random.uniform(4, 7))  # Allow page to fully load
    text = driver.find_element(By.TAG_NAME, "body").text
    filename = os.path.join(TXT_DIR, f"job_{idx + 1}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    return filename

def parse_job_text(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    # Extract Title before 'Posted' line
    title = ""
    for i, line in enumerate(lines):
        if re.search(r"Posted\s+.*ago", line, re.I):
            title = lines[i - 1] if i > 0 else ""
            break

    # Extract Posted line
    posted = next((l for l in lines if re.search(r"Posted\s+.*ago", l, re.I)), "")

    # Extract summary boundaries and summary text
    summary_start = None
    summary_end = None
    for i, line in enumerate(lines):
        if "Summary" in line or "Description" in line:
            summary_start = i + 1
        if summary_start is not None and (
            re.search(r"\$\d", line) or "Budget" in line or "Fixed Price" in line or "Hourly Rate" in line
        ):
            summary_end = i
            break
    summary = " ".join(lines[summary_start:summary_end]) if summary_start is not None and summary_end is not None else ""

    # Hours Based: search only inside Summary/Description block
    hoursbased = ""
    if summary_start is not None and summary_end is not None:
        for line in lines[summary_start:summary_end]:
            if re.search(r"hour", line, re.I) or re.search(r"hour based", line, re.I) or re.search(r"hours?", line, re.I):
                hoursbased = line
                break

    # Hourly Rate search (outside summary block)
    hourly = ""
    for i in range(summary_end if summary_end is not None else 0, len(lines)):
        line = lines[i]
        hourly_match = re.search(r"\$([\d]+)\s*-\s*\$([\d]+)", line)
        if hourly_match:
            hourly = hourly_match.group(0)
            break
        m = re.search(r"\$[\d,\.Kk]+", line)
        if m:
            hourly = m.group()
            break

    # Invites Sent: numeric value between "Interviewing:" and "Unanswered invites:"
    invites_sent = ""
    activity_index = next((i for i, l in enumerate(lines) if "Activity on this job" in l), None)
    if activity_index is not None:
        relevant_lines = lines[activity_index + 1 : activity_index + 20]
        interviewing_idx = next((idx for idx, l in enumerate(relevant_lines) if l.startswith("Interviewing:")), None)
        unanswered_idx = next((idx for idx, l in enumerate(relevant_lines) if l.startswith("Unanswered invites:")), None)
        if interviewing_idx is not None and unanswered_idx is not None and unanswered_idx > interviewing_idx:
            between_lines = relevant_lines[interviewing_idx + 1 : unanswered_idx]
            for line in reversed(between_lines):
                nums = re.findall(r"\d+", line)
                if nums:
                    invites_sent = nums[-1]
                    break

    # About the client and hires extraction
    member_since = location = spent = hires = ""
    about_index = next((i for i, l in enumerate(lines) if l.startswith("About the client")), None)
    if about_index is not None:
        client_block = " ".join(lines[about_index : about_index + 7])
        m = re.search(r"Member since ([\w\s,]+)", client_block)
        if m: member_since = m.group(1).strip()
        m = re.search(r"Member since [\w\s,]+ ([\w\s]+) \d{1,2}:\d{2}", client_block)
        if m: location = m.group(1).strip()
        m = re.search(r"(\$[\d\.,Kk]+) total spent", client_block)
        if m: spent = m.group(1)
        m = re.search(r"(\d+) hires", client_block)
        if m: hires = m.group(1)

    # Hires1: numeric value found after "Last viewed by client:" and before "Interviewing:" section
    hires1 = ""
    last_viewed_index = next((i for i, l in enumerate(lines) if l.startswith("Last viewed by client:")), None)
    interviewing_index = next((i for i, l in enumerate(lines) if l.startswith("Interviewing:")), None)
    if last_viewed_index is not None and interviewing_index is not None and interviewing_index > last_viewed_index:
        for idx in range(last_viewed_index + 1, interviewing_index):
            if lines[idx].startswith("Hires:"):
                # Check for inline numeric value in the same line
                m = re.search(r"Hires:\s*(\d+)", lines[idx])
                if m:
                    hires1 = m.group(1)
                    break
                # Check next line after "Hires:"
                for look_ahead in range(idx + 1, interviewing_index):
                    m2 = re.search(r"\d+", lines[look_ahead])
                    if m2:
                        hires1 = m2.group(0)
                        break
                if hires1:
                    break

    return {
        "title": title,
        "posted": posted,
        "summary": summary,
        "hourly": hourly,
        "hoursbased": hoursbased,
        "invites_sent": invites_sent,
        "member_since": member_since,
        "location": location,
        "spent": spent,
        "hires": hires,
        "hires1": hires1,
        "file": os.path.basename(file_path),
    }

def run():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.186 Safari/537.36"
    )

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 30)

    links = collect_job_links(driver, wait)

    txt_files = []
    for idx, url in enumerate(links):
        try:
            txt_file = save_job_text(driver, url, idx)
            logging.info(f"Saved job text #{idx + 1}: {url}")
            txt_files.append((url, txt_file))
        except Exception as e:
            logging.error(f"Failed to save job text for {url}: {e}")
        time.sleep(2)

    try:
        driver.quit()
    except Exception:
        pass

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Job Link", "Title", "Posted", "Summary",
                "Hourly Rate", "Hours Based", "Invites Sent",
                "Member Since", "Location", "Spent", "Hires", "Hires1", "Source File"
            ]
        )
        for url, txt_file in txt_files:
            parsed = parse_job_text(txt_file)
            writer.writerow(
                [
                    url,
                    parsed["title"],
                    parsed["posted"],
                    parsed["summary"],
                    parsed["hourly"],
                    parsed["hoursbased"],
                    parsed["invites_sent"],
                    parsed["member_since"],
                    parsed["location"],
                    parsed["spent"],
                    parsed["hires"],
                    parsed["hires1"],
                    parsed["file"],
                ]
            )
    logging.info(f"Scraped job details saved to {CSV_FILE}")

if __name__ == "__main__":
    run()
