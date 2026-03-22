import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import csv
import os
import getpass
import warnings
import logging

# Suppress undetected_chromedriver warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger('undetected_chromedriver').setLevel(logging.CRITICAL)

# Upwork job search URL
url = 'https://www.upwork.com/nx/search/jobs/?nbs=1&q=lead%20generation&page=15&per_page=50&nav_dir=pop'

# Set up headless undetected Chrome
options = uc.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = uc.Chrome(options=options, headless=True)

# Extract Downloads folder path for current user
downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
csv_filename = os.path.join(downloads_folder, "upwork_jobs_lead_generation.csv")

try:
    driver.get(url)
    time.sleep(7)  # Wait for Cloudflare and full page load

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    jobs = []

    # Parse job cards
    for card in soup.find_all('section', {'data-test': 'job-tile-list-section'}):
        for job in card.find_all('div', {'data-test': 'job-tile'}):
            title = job.find('a', {'data-test': 'job-title-link'})
            title = title.text.strip() if title else ''
            description = job.find('span', {'data-test': 'job-description-text'})
            description = description.text.strip() if description else ''
            category = job.find('span', {'data-test': 'job-category'})
            category = category.text.strip() if category else ''
            hourly_rate = job.find('span', {'data-test': 'job-type-label'})
            hourly_rate = hourly_rate.text.strip() if hourly_rate else ''
            posted = job.find('span', {'data-test': 'posted-on'})
            posted = posted.text.strip() if posted else ''
            # You may extract more fields here as needed

            jobs.append({
                'Title': title,
                'Description': description,
                'Category': category,
                'Hourly/Fixed': hourly_rate,
                'Posted': posted
            })
finally:
    try:
        driver.quit()
        del driver
    except Exception:
        pass  # Ignore Windows handle warning

# Write data to CSV in Downloads folder
if jobs:
    keys = jobs[0].keys()
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(jobs)
    print(f"Scraped data saved to: {csv_filename}")
else:
    print("No jobs found or scraping failed.")
