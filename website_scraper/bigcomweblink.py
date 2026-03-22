import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse
import os
from datetime import datetime
import logging

class UnifiedCompanyExtractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.skip_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'google.com', 'microsoft.com', 'github.com',
            'app.', 'api.', 'support.', 'help.', 'docs.',
            'blog.', 'news.', 'mail.', 'email.', 'contact.', 'schema.org'
        ]
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def extract_company_details(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            company_name = self._extract_company_name_from_title_area(soup, url)
            company_website = self._extract_website_from_website_section(soup, url)
            return company_name, company_website
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return "", ""

    def _extract_company_name_from_title_area(self, soup, url):
        company_name = ""
        for heading_tag in ['h1', 'h2']:
            headings = soup.find_all(heading_tag)
            for heading in headings[:2]:
                text = heading.get_text().strip()
                if text and len(text) < 100:
                    if not any(skip in text.lower() for skip in ['integration', 'marketplace', 'x ', '|']):
                        company_name = text
                        break
            if company_name:
                break
        if not company_name:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text().strip()
                if 'x ' in title_text:
                    parts = title_text.split('x ')
                    if len(parts) > 1:
                        company_name = parts[1].split('|')[0].split('-')[0].strip()
                elif '|' in title_text:
                    company_name = title_text.split('|')[0].strip()
                elif '-' in title_text:
                    company_name = title_text.split('-')[0].strip()
                else:
                    company_name = title_text
                company_name = re.sub(r'\s*(integration|marketplace|app store).*$', '', company_name, flags=re.IGNORECASE)
        if not company_name or len(company_name) < 2:
            path_parts = urlparse(url).path.split('/')
            for part in reversed(path_parts):
                if part and part not in ['marketplace', 'products', 'integration', 'app', 'en']:
                    company_name = part.replace('-', ' ').replace('_', ' ').title()
                    break
        return company_name.strip()

    def _extract_website_from_website_section(self, soup, url):
        company_website = ""
        # Method 1: Ctrl-A/Copy all visible text extraction
        body_text = soup.get_text(separator='\n', strip=True)
        website_candidates = re.findall(r'(https?://[^\s\)\(]+)', body_text)
        for candidate in website_candidates:
            if '.' in candidate and len(candidate) > 10 and not any(skip in candidate for skip in self.skip_domains):
                if candidate.startswith('http'):
                    company_website = candidate.strip()
                    break
        # Method 2: Tag/Class-ID based as per your red/green circles
        if not company_website:
            for p_tag in soup.find_all('p', class_='details-website'):
                a_tag = p_tag.find('a', href=True)
                if a_tag:
                    candidate = a_tag['href'].strip()
                    if candidate.startswith('http') and not any(skip in candidate for skip in self.skip_domains):
                        company_website = candidate
                        break
        if not company_website:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].strip()
                if href.startswith('http') and not any(skip in href for skip in self.skip_domains):
                    if '.' in href and len(href) > 10:
                        company_website = href
                        break
        if company_website and '?' in company_website:
            company_website = company_website.split('?')[0]
        return company_website.strip()

    def process(self, input_data, output_file=None, batch_size=50, processing_mode="auto"):
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"extracted_company_data_{timestamp}.csv"
        df = self._load_data(input_data)
        if df is None:
            return None, None
        total_rows = len(df)
        if processing_mode == "auto":
            processing_mode = "batch" if total_rows > 20 else "single"
        if processing_mode == "batch" and total_rows > batch_size:
            return self._process_in_batches(df, output_file, batch_size)
        else:
            return self._process_single(df, output_file)

    def _load_data(self, input_data):
        try:
            if isinstance(input_data, pd.DataFrame):
                return input_data
            elif isinstance(input_data, str):
                if input_data.endswith('.csv'):
                    if os.path.exists(input_data):
                        return pd.read_csv(input_data)
                    else:
                        print(f"❌ File not found: {input_data}")
                        return None
                else:
                    from io import StringIO
                    return pd.read_csv(StringIO(input_data))
            else:
                raise ValueError("Input must be CSV file path, CSV content string, or DataFrame")
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            print(f"❌ Error loading data: {str(e)}")
            return None

    def _process_single(self, df, output_file):
        output_data = []
        total_links = len(df)
        print(f"🔄 Starting extraction for {total_links} reference links...")
        for idx, row in df.iterrows():
            reference_link = row['Reference links'].strip()
            print(f"🔍 Processing {idx + 1}/{total_links}: {reference_link[:60]}...")
            company_name, company_website = self.extract_company_details(reference_link)
            output_data.append({
                'Reference Link': reference_link,
                'Company Name': company_name,
                'Company Website': company_website,
                'Extraction Status': 'Success' if (company_name or company_website) else 'Failed'
            })
            print(f"  🟢 Company Name: '{company_name}'")
            print(f"  🔴 Company Website: '{company_website}'")
            print("-" * 40)
            time.sleep(1)
        output_df = pd.DataFrame(output_data)
        output_df.to_csv(output_file, index=False)
        summary = self._generate_summary(output_df, output_file)
        self._print_summary(summary)
        return output_df, summary

    def _process_in_batches(self, df, output_base_file, batch_size):
        total_rows = len(df)
        output_dir = os.path.splitext(output_base_file)[0] + "_batches"
        os.makedirs(output_dir, exist_ok=True)
        all_results = []
        batch_summaries = []
        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            batch_df = df.iloc[start_idx:end_idx]
            batch_num = (start_idx // batch_size) + 1
            batch_output = os.path.join(output_dir, f"batch_{batch_num:03d}_results.csv")
            print(f"\n📦 Processing Batch {batch_num}: rows {start_idx+1} to {end_idx}")
            batch_results, batch_summary = self._process_single(batch_df, batch_output)
            all_results.append(batch_results)
            batch_summaries.append(batch_summary)
        final_df = pd.concat(all_results, ignore_index=True)
        final_output = output_base_file
        final_df.to_csv(final_output, index=False)
        final_summary = {
            'total_processed': total_rows,
            'total_batches': len(batch_summaries),
            'successful_extractions': sum(s['successful_extractions'] for s in batch_summaries),
            'companies_with_names': sum(s['companies_with_names'] for s in batch_summaries),
            'companies_with_websites': sum(s['companies_with_websites'] for s in batch_summaries),
            'output_file': final_output,
            'batch_directory': output_dir
        }
        print(f"\n🎉 BATCH PROCESSING COMPLETE!")
        print(f"📊 Total Processed: {final_summary['total_processed']}")
        print(f"💾 Combined Results: {final_summary['output_file']}")
        print(f"📁 Individual Batches: {final_summary['batch_directory']}")
        return final_df, final_summary

    def _generate_summary(self, output_df, output_file):
        return {
            'total_processed': len(output_df),
            'successful_extractions': len(output_df[output_df['Extraction Status'] == 'Success']),
            'companies_with_names': len(output_df[output_df['Company Name'] != '']),
            'companies_with_websites': len(output_df[output_df['Company Website'] != '']),
            'output_file': output_file
        }

    def _print_summary(self, summary):
        print("\n" + "="*60)
        print("📈 PROCESSING SUMMARY")
        print("="*60)
        print(f"📊 Total links processed: {summary['total_processed']}")
        print(f"🎯 Successful extractions: {summary['successful_extractions']}")
        print(f"🏢 Companies with names: {summary['companies_with_names']}")
        print(f"🌐 Companies with websites: {summary['companies_with_websites']}")
        print(f"💾 Output saved to: {summary['output_file']}")
        print("="*60)
        print("✅ PROCESSING COMPLETE!")

def main():
    extractor = UnifiedCompanyExtractor()
    input_file = "webreflink.csv"
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found in current directory!")
        print(f"📁 Current directory: {os.getcwd()}")
        return
    print(f"📁 Found input file: {input_file}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"company_data_extracted_{timestamp}.csv"
    print(f"💾 Output will be saved to: {output_file}")
    print("\n🚀 Starting processing...")
    try:
        result_df, summary = extractor.process(input_file, output_file)
        if result_df is not None:
            print(f"\n🎊 SUCCESS! Processing completed successfully!")
            print(f"📄 Check your results in: {summary['output_file']}")
            if len(result_df) > 0:
                print(f"\n👀 PREVIEW OF RESULTS (First 5 rows):")
                print("=" * 80)
                preview = result_df[['Company Name', 'Company Website', 'Extraction Status']].head()
                print(preview.to_string(index=False))
                print("=" * 80)
                success_rate = (summary['successful_extractions'] / summary['total_processed']) * 100
                print(f"\n📈 SUCCESS RATE: {success_rate:.1f}% ({summary['successful_extractions']}/{summary['total_processed']})")
        else:
            print("❌ Processing failed. Please check the error messages above.")
    except Exception as e:
        print(f"❌ Unexpected error occurred: {str(e)}")
        print("Please check your input file format and try again.")

if __name__ == "__main__":
    main()
else:
    print("\n" + "="*60)
    print("🎯 READY TO PROCESS webreflink.csv")
    print("📋 Usage: python mewsweblink.py")
    print("✅ Will automatically find and process webreflink.csv")
    print("💾 Output: company_data_extracted_[timestamp].csv")
    print("="*60)
