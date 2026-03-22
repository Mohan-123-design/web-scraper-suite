import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import os
import time

INPUTFILE = "webreflink1.csv"  # <-- updated; auto loads from working folder
OUTPUTFILE = "companywebsiteextracted.csv"
REFERENCELINKS_COL = "Reference links"

def extract_company_and_website(soup):
    # Try to extract company name from main headings (red circle, h1/h2)
    company_name = ""
    for tag in ['h1', 'h2']:
        for el in soup.find_all(tag):
            txt = el.get_text(strip=True)
            if txt and len(txt) > 2 and len(txt) < 100:
                company_name = txt
                break
        if company_name:
            break
    # Fallback to title tag if not found
    if not company_name:
        t = soup.find('title')
        if t:
            raw = t.get_text(strip=True)
            company_name = raw.split("-")[0].strip() if "-" in raw else raw

    company_website = ""
    # First, look for divs/buttons/links matching "visit website" or "view website" (case-insensitive) - green circle reference
    for a in soup.find_all(['a', 'button'], string=re.compile(r'visit website|view website', re.I)):
        if a.has_attr('href') and a['href'].startswith("http"):
            company_website = a['href']
            break
    # Fallback by searching for any <a> whose text contains relevant website words and is not a known excluded domain
    if not company_website:
        EXCLUDE = ['linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 'google.com',
                   'microsoft.com', 'github.com', 'app.', 'api.', 'support.', 'help.', 'docs.', 'blog.', 'news.',
                   'mail.', 'email.', 'contact.', 'schema.org']
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True).lower() if a.get_text() else ""
            href = a['href'].strip()
            if any(k in text for k in ["visit website", "view website", "website"]) and href.startswith("http"):
                # Exclude certain domains/patterns
                if not any(ex in href for ex in EXCLUDE):
                    company_website = href
                    break
    return company_name, company_website

def main():
    if not os.path.exists(INPUTFILE):
        print(f"Input file {INPUTFILE} not found!")
        return

    df = pd.read_csv(INPUTFILE)
    results = []
    for idx, row in df.iterrows():
        ref = row.get(REFERENCELINKS_COL, "").strip()
        print(f"Processing {idx+1}/{len(df)}: {ref}")
        if not ref.startswith("http"):
            results.append({"Reference Link": ref, "Company Name": "", "Company Website": "", "Status": "Invalid URL"})
            continue
        try:
            resp = requests.get(ref, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            name, website = extract_company_and_website(soup)
            results.append({
                "Reference Link": ref,
                "Company Name": name,
                "Company Website": website,
                "Status": "Success" if (name or website) else "Not Found"
            })
        except Exception as e:
            results.append({
                "Reference Link": ref,
                "Company Name": "",
                "Company Website": "",
                "Status": f"Error: {e}"
            })
        time.sleep(1)  # Optional polite delay

    pd.DataFrame(results).to_csv(OUTPUTFILE, index=False)
    print(f"Extraction complete. Results saved to {OUTPUTFILE}.")

if __name__ == "__main__":
    main()
