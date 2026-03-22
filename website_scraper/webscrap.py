import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import re

input_csv = 'webreflink.csv'
output_csv = 'company_website_extracted.csv'

def extract_company_name_and_website(soup):
    company_name = ''
    company_website = ''
    # Company Name - try all circled heading areas (red)
    candidates = soup.find_all(['h1','h2','span','div','p'])
    for h in candidates:
        txt = h.get_text(strip=True)
        # Example, match by content shown in red circle
        if txt and (txt.lower().startswith('configcat') or "feature flags" in txt.lower()):
            company_name = txt
            break
    # Fallback: try <title>
    if not company_name:
        t = soup.find('title')
        if t:
            company_name = t.get_text().split('|')[0].strip()
    # Website Link - button/link text marked green in sample
    for link in soup.find_all(['a', 'button'], string=re.compile(r'(visit website|website|configcat website)', re.IGNORECASE)):
        if link.has_attr('href'):
            company_website = link['href']
            break
    # Fallback: use any 'a' tag with relevant text and domain filter
    if not company_website:
        for a in soup.find_all('a'):
            link_text = a.get_text(strip=True).lower()
            href = a.get('href','')
            if href and href.startswith('http') and (
                'visit website' in link_text or 'website' in link_text):
                if not any(ex in href for ex in ['linkedin.com','facebook.com','twitter.com',
                                                 'docs.','api.','support.','help.','blog.']):
                    company_website = href
                    break
    return company_name, company_website

if not os.path.exists(input_csv):
    print(f"Input file '{input_csv}' not found!")
    raise FileNotFoundError(input_csv)

df = pd.read_csv(input_csv)
results = []
for idx, row in df.iterrows():
    ref = row.get('Reference links','')
    print(f"Processing {idx+1}/{len(df)}: {ref}")
    if not ref or not str(ref).startswith('http'):
        results.append({'Reference Link': ref, 'Company Name': '', 'Company Website': ''})
        continue
    try:
        resp = requests.get(ref, timeout=20, headers={'User-Agent':'Mozilla/5.0'})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        company_name, company_website = extract_company_name_and_website(soup)
    except Exception as e:
        company_name, company_website = '', ''
        print(f"Error on {ref}: {e}")
    results.append({'Reference Link': ref, 'Company Name': company_name, 'Company Website': company_website})
    time.sleep(1)
outdf = pd.DataFrame(results)
outdf.to_csv(output_csv, index=False)
print(f"Extraction complete. Results saved to {output_csv}.")
