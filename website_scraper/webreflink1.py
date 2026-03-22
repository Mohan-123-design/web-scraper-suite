import os
import csv
import time
import requests
from bs4 import BeautifulSoup

# Input and output filenames
INPUT_CSV = 'comreflink.csv'
OUTPUT_CSV = 'extracted_company_websites.csv'

# User-Agent header for HTTP requests
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.7339.186 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT
}

def extract_website_url(soup):
    """
    Extract the company website URL from section under <h4> with text 'Go to website:'.
    The URL is inside <p class="tw-mt-2"> containing an <a> tag.
    """
    try:
        h4_tags = soup.find_all('h4')
        for h4 in h4_tags:
            if h4.get_text(strip=True).lower() == 'go to website:':
                # The URL is inside the next <p> sibling with class "tw-mt-2"
                p_tag = h4.find_next_sibling('p', class_='tw-mt-2')
                if p_tag:
                    a_tag = p_tag.find('a', href=True)
                    if a_tag and a_tag['href'].startswith('http'):
                        return a_tag['href'].strip()
        return ""
    except Exception as e:
        # If any error occurs, just return empty string
        return ""

def main():
    # Check if input CSV file exists in current folder
    if not os.path.exists(INPUT_CSV):
        print(f"[Error] Input file '{INPUT_CSV}' not found in the current directory.")
        return
    
    results = []
    
    # Read input CSV and identify reference link column (case-insensitive search)
    with open(INPUT_CSV, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        ref_col = None
        # Find the column which contains both 'reference' and 'link'
        for col in reader.fieldnames:
            if 'reference' in col.lower() and 'link' in col.lower():
                ref_col = col
                break
        
        if not ref_col:
            print("[Error] Could not find 'reference link' column in input CSV.")
            return
        
        input_rows = list(reader)
    
    # Iterate over each row and scrape company website URL
    for idx, row in enumerate(input_rows, 1):
        ref_link = row[ref_col].strip()
        if not ref_link.lower().startswith(("http://", "https://")):
            print(f"[{idx}/{len(input_rows)}] Skipping invalid URL: {ref_link}")
            results.append({'Reference Link': ref_link, 'Company Website': '', 'Status': 'Invalid URL'})
            continue
        
        try:
            print(f"[{idx}/{len(input_rows)}] Processing: {ref_link}")
            response = requests.get(ref_link, headers=HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            website_url = extract_website_url(soup)
            status = 'Success' if website_url else 'Website URL Not Found'
            
            results.append({
                'Reference Link': ref_link,
                'Company Website': website_url,
                'Status': status
            })
        except Exception as e:
            print(f"[{idx}/{len(input_rows)}] Error processing {ref_link}: {e}")
            results.append({
                'Reference Link': ref_link,
                'Company Website': '',
                'Status': f'Error: {e}'
            })
        
        # Sleep 1 second between requests to avoid hammering server
        time.sleep(1)
    
    # Write output CSV file with results
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['Reference Link', 'Company Website', 'Status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow(res)
    
    print(f"\nExtraction completed. Results saved to '{OUTPUT_CSV}'.")

if __name__ == "__main__":
    main()
