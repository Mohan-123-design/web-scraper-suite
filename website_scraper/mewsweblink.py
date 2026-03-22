# COMPLETE UNIFIED COMPANY DATA EXTRACTION SYSTEM
# File: mewsweblink.py
# Automatically processes webreflink.csv file

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
import csv
from io import StringIO
import os
from datetime import datetime
import logging

class UnifiedCompanyExtractor:
    """
    Complete unified system for extracting company information from reference links
    Automatically processes webreflink.csv file
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.skip_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'google.com', 'microsoft.com', 'github.com',
            'mews.com', 'app.', 'api.', 'support.', 'help.', 'docs.',
            'blog.', 'news.', 'mail.', 'email.', 'contact.', 'schema.org'
        ]
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        print("🚀 UNIFIED COMPANY DATA EXTRACTION SYSTEM")
        print("="*60)
        print("✅ Extracts from GREEN CIRCLE (company names)")
        print("✅ Extracts from RED CIRCLE (company websites)")
        print("✅ Processes webreflink.csv automatically")
        print("="*60)
    
    def extract_company_details(self, url):
        """Extract company name and website from reference link"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract company name - GREEN CIRCLE area
            company_name = self._extract_company_name_from_title_area(soup, url)
            
            # Extract company website - RED CIRCLE area
            company_website = self._extract_website_from_website_section(soup, url)
            
            return company_name, company_website
            
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return "", ""
    
    def _extract_company_name_from_title_area(self, soup, url):
        """Extract company name from GREEN CIRCLE area"""
        company_name = ""
        
        # Method 1: Look for main headings (h1, h2)
        for heading_tag in ['h1', 'h2']:
            headings = soup.find_all(heading_tag)
            for heading in headings[:2]:
                text = heading.get_text().strip()
                if text and len(text) < 100:
                    # Clean up and validate company name
                    if not any(skip in text.lower() for skip in ['mews', 'integration', 'marketplace', 'x ', '|']):
                        company_name = text
                        break
            if company_name:
                break
        
        # Method 2: Extract from page title tag
        if not company_name:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text().strip()
                
                # Clean up title to get company name
                if 'x ' in title_text:  # Handle "Mews x CompanyName" format
                    parts = title_text.split('x ')
                    if len(parts) > 1:
                        company_name = parts[1].split('|')[0].split('-')[0].strip()
                elif '|' in title_text:
                    company_name = title_text.split('|')[0].strip()
                elif '-' in title_text:
                    company_name = title_text.split('-')[0].strip()
                else:
                    company_name = title_text
                
                # Clean up extracted name
                company_name = re.sub(r'\s*(integration|marketplace|app store).*$', '', company_name, flags=re.IGNORECASE)
                company_name = company_name.replace('Mews x ', '').replace('Mews ', '').strip()
        
        # Method 3: Extract from URL structure (fallback)
        if not company_name or len(company_name) < 2:
            path_parts = urlparse(url).path.split('/')
            for part in reversed(path_parts):
                if part and part not in ['marketplace', 'products', 'integration', 'app', 'en']:
                    company_name = part.replace('-', ' ').replace('_', ' ').title()
                    break
        
        return company_name.strip()
    
    def _extract_website_from_website_section(self, soup, url):
        """Extract company website from RED CIRCLE area"""
        company_website = ""
        
        # Method 1: Look specifically for "Website" text and nearby content
        for element in soup.find_all(['div', 'span', 'p', 'td', 'th', 'label']):
            if element.string and 'website' in element.string.lower():
                parent = element.parent
                if parent:
                    full_text = parent.get_text()
                    
                    # Extract domain from text
                    domain_patterns = [
                        r'www\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                        r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
                    ]
                    
                    for pattern in domain_patterns:
                        matches = re.findall(pattern, full_text)
                        for match in matches:
                            domain = match.lower().replace('www.', '')
                            if not any(skip in domain for skip in self.skip_domains):
                                if len(domain) > 4 and len(domain) < 50:
                                    company_website = domain
                                    break
                        if company_website:
                            break
                            
                    if company_website:
                        break
        
        # Method 2: Look for external links (as fallback)
        if not company_website:
            links = soup.find_all('a', href=True)
            external_domains = set()
            
            for link in links:
                href = link.get('href', '').strip()
                if href.startswith('http'):
                    try:
                        parsed = urlparse(href)
                        domain = parsed.netloc.lower().replace('www.', '')
                        
                        # Skip unwanted domains
                        if not any(skip in domain for skip in self.skip_domains):
                            if '.' in domain and len(domain) > 4 and len(domain) < 50:
                                # Prioritize .com domains
                                if domain.endswith('.com'):
                                    external_domains.add(domain)
                                elif not any(d.endswith('.com') for d in external_domains):
                                    external_domains.add(domain)
                    except:
                        continue
            
            # Pick the best domain
            if external_domains:
                # Prefer .com domains, then shortest
                com_domains = [d for d in external_domains if d.endswith('.com')]
                if com_domains:
                    company_website = min(com_domains, key=len)
                else:
                    company_website = min(external_domains, key=len)
        
        return company_website.strip()
    
    def process(self, input_data, output_file=None, batch_size=50, processing_mode="auto"):
        """UNIFIED PROCESSING METHOD - Handles ALL input formats"""
        
        # Auto-generate output filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"extracted_company_data_{timestamp}.csv"
        
        # Determine input type and load data
        df = self._load_data(input_data)
        if df is None:
            return None, None
        
        total_rows = len(df)
        print(f"📊 Loaded {total_rows} reference links for processing")
        
        # Determine processing mode
        if processing_mode == "auto":
            processing_mode = "batch" if total_rows > 20 else "single"
        
        print(f"⚙️ Using {processing_mode} processing mode")
        
        # Process based on mode
        if processing_mode == "batch" and total_rows > batch_size:
            return self._process_in_batches(df, output_file, batch_size)
        else:
            return self._process_single(df, output_file)
    
    def _load_data(self, input_data):
        """Load data from various input formats"""
        try:
            if isinstance(input_data, pd.DataFrame):
                return input_data
            elif isinstance(input_data, str):
                if input_data.endswith('.csv'):
                    # File path
                    if os.path.exists(input_data):
                        return pd.read_csv(input_data)
                    else:
                        print(f"❌ File not found: {input_data}")
                        return None
                else:
                    # CSV content string
                    return pd.read_csv(StringIO(input_data))
            else:
                raise ValueError("Input must be CSV file path, CSV content string, or DataFrame")
                
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            print(f"❌ Error loading data: {str(e)}")
            return None
    
    def _process_single(self, df, output_file):
        """Process all rows in single batch"""
        output_data = []
        total_links = len(df)
        
        print(f"🔄 Starting extraction for {total_links} reference links...")
        print("="*60)
        
        for idx, row in df.iterrows():
            reference_link = row['Reference links'].strip()
            
            print(f"🔍 Processing {idx + 1}/{total_links}: {reference_link[:60]}...")
            
            # Extract company details
            company_name, company_website = self.extract_company_details(reference_link)
            
            # Add to output data
            output_data.append({
                'Reference Link': reference_link,
                'Company Name': company_name,
                'Company Website': company_website,
                'Extraction Status': 'Success' if (company_name or company_website) else 'Failed'
            })
            
            print(f"  🟢 Company Name: '{company_name}'")
            print(f"  🔴 Company Website: '{company_website}'")
            print("-" * 40)
            
            # Respectful delay
            time.sleep(1)
        
        # Create and save output
        output_df = pd.DataFrame(output_data)
        output_df.to_csv(output_file, index=False)
        
        # Generate summary
        summary = self._generate_summary(output_df, output_file)
        self._print_summary(summary)
        
        return output_df, summary
    
    def _process_in_batches(self, df, output_base_file, batch_size):
        """Process large datasets in batches"""
        total_rows = len(df)
        output_dir = os.path.splitext(output_base_file)[0] + "_batches"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"📁 Processing {total_rows} rows in batches of {batch_size}")
        print("="*60)
        
        all_results = []
        batch_summaries = []
        
        # Process in batches
        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            batch_df = df.iloc[start_idx:end_idx]
            
            batch_num = (start_idx // batch_size) + 1
            batch_output = os.path.join(output_dir, f"batch_{batch_num:03d}_results.csv")
            
            print(f"\n📦 Processing Batch {batch_num}: rows {start_idx+1} to {end_idx}")
            print("-" * 50)
            
            # Process batch
            batch_results, batch_summary = self._process_single(batch_df, batch_output)
            
            all_results.append(batch_results)
            batch_summaries.append(batch_summary)
            
            print(f"✅ Batch {batch_num} complete: {batch_summary['successful_extractions']}/{len(batch_df)} successful")
        
        # Combine all results
        final_df = pd.concat(all_results, ignore_index=True)
        final_output = output_base_file
        final_df.to_csv(final_output, index=False)
        
        # Generate final summary
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
        """Generate processing summary"""
        return {
            'total_processed': len(output_df),
            'successful_extractions': len(output_df[output_df['Extraction Status'] == 'Success']),
            'companies_with_names': len(output_df[output_df['Company Name'] != '']),
            'companies_with_websites': len(output_df[output_df['Company Website'] != '']),
            'output_file': output_file
        }
    
    def _print_summary(self, summary):
        """Print processing summary"""
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
    """Main function to process webreflink.csv automatically"""
    
    # Initialize the extractor
    extractor = UnifiedCompanyExtractor()
    
    # Check if webreflink.csv exists
    input_file = "webreflink.csv"
    
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found in current directory!")
        print(f"📁 Current directory: {os.getcwd()}")
        print(f"📋 Available CSV files:")
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        if csv_files:
            for file in csv_files:
                print(f"   📄 {file}")
        else:
            print("   (No CSV files found)")
        
        print(f"\n💡 Please ensure {input_file} is in the same directory as this script.")
        print(f"📋 The CSV file should have a column named 'Reference links'")
        return
    
    print(f"📁 Found input file: {input_file}")
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"company_data_extracted_{timestamp}.csv"
    
    print(f"💾 Output will be saved to: {output_file}")
    print("\n🚀 Starting processing...")
    
    try:
        # Process the file
        result_df, summary = extractor.process(input_file, output_file)
        
        if result_df is not None:
            print(f"\n🎊 SUCCESS! Processing completed successfully!")
            print(f"📄 Check your results in: {summary['output_file']}")
            
            # Show a preview of the results
            if len(result_df) > 0:
                print(f"\n👀 PREVIEW OF RESULTS (First 5 rows):")
                print("=" * 80)
                preview = result_df[['Company Name', 'Company Website', 'Extraction Status']].head()
                print(preview.to_string(index=False))
                print("=" * 80)
                
                # Show success rate
                success_rate = (summary['successful_extractions'] / summary['total_processed']) * 100
                print(f"\n📈 SUCCESS RATE: {success_rate:.1f}% ({summary['successful_extractions']}/{summary['total_processed']})")
            
        else:
            print("❌ Processing failed. Please check the error messages above.")
            
    except Exception as e:
        print(f"❌ Unexpected error occurred: {str(e)}")
        print("Please check your input file format and try again.")

# Run the main function when script is executed
if __name__ == "__main__":
    main()
else:
    print("\n" + "="*60)
    print("🎯 READY TO PROCESS webreflink.csv")
    print("📋 Usage: python mewsweblink.py")
    print("✅ Will automatically find and process webreflink.csv")
    print("💾 Output: company_data_extracted_[timestamp].csv")
    print("="*60)
