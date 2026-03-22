# Web Scraper Suite

A collection of Python web scrapers targeting different website types — company directories, healthcare provider pages, hotel management platforms (Mews, BigCommerce), and medical databases. Uses both Requests+BeautifulSoup for static pages and Selenium for JavaScript-heavy sites.

## Scrapers Included

| Folder | Target | Method |
|--------|--------|--------|
| `website_scraper/` | Company directories, Mews, BigCommerce, general sites | Requests + Selenium |
| `scraper_backup/` | Multi-version scraper iterations for lead generation | Requests + BeautifulSoup |
| `doctor_webmd/` | Doctor profiles from WebMD using Perplexity API | API-assisted |

## website_scraper (Main)

Extracts company names, websites, and contact details from reference link lists.

**Key files:**
- `mewsweblink.py` — scrapes Mews hotel management platform listings
- `bigcomweblink.py` — scrapes BigCommerce merchant directories
- `reflink.py` / `webreflink*.py` — processes reference CSV lists to find company websites
- `comsearch.py` — company search and data extraction

```bash
pip install -r requirements.txt
# Place input CSV in working directory
python reflink.py
```

## doctor_webmd

Uses Perplexity API to find and extract WebMD profile URLs for doctors given their names and specialties.

```bash
pip install requests pandas
# Add PERPLEXITY_API_KEY to environment
python "doctor webmd link using perplexity api.py"
```

## Strategy Selection

The scrapers automatically pick the right approach per target:
- **Static pages** → Requests + BeautifulSoup (fast, lightweight)
- **JS-heavy pages** → Selenium + ChromeDriver (handles dynamic content)
- **AI-assisted lookup** → Perplexity API (for hard-to-scrape or paywalled content)

## Tech Stack

- Python, Requests, BeautifulSoup4
- Selenium, ChromeDriver
- Perplexity API
- Pandas, CSV

## Environment Variables

```
PERPLEXITY_API_KEY=your_key
```

## Notes

- ChromeDriver version must match your installed Chrome browser version
- Large output CSVs are excluded from this repo (in .gitignore) — run the scrapers to generate them
