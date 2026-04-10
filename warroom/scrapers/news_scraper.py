"""
News scraper for Tamil news sites.
Scrapes articles mentioning the target constituency/district and stores in social_sentiment table.

Targets: Dinamani, Dinathanthi, Vikatan, The Hindu Tamil
Uses respectful rate limiting and proper Tamil UTF-8 handling.

Usage:
    python news_scraper.py                  # Scrape all sources
    python news_scraper.py --source dinamani  # Single source
    python news_scraper.py --import news.csv  # Import from CSV fallback
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, date
from urllib.parse import quote_plus

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_db

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPING = True
except ImportError:
    HAS_SCRAPING = False

# Configuration
CONSTITUENCY = "TIRUTTANI"
CONSTITUENCY_TAMIL = "திருத்தணி"
DISTRICT = "TIRUVALLUR"
DISTRICT_TAMIL = "திருவள்ளூர்"
MLA_NAME = "S.Chandran"
MLA_NAME_TAMIL = "சந்திரன்"

RATE_LIMIT_SECONDS = 3  # Respectful delay between requests
MAX_PAGES = 5  # Max pages per source per run

SEARCH_TERMS = [
    CONSTITUENCY_TAMIL,
    DISTRICT_TAMIL,
    "Tiruttani",
    "Tiruvallur",
    MLA_NAME_TAMIL,
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ta,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

# Issue category keywords for auto-tagging
CATEGORY_KEYWORDS = {
    "water": ["நீர்", "water", "குடிநீர்", "drinking water", "வெள்ளம்", "flood", "drought", "வறட்சி", "bore well", "ஆறு"],
    "roads": ["சாலை", "road", "bridge", "பாலம்", "pothole", "குழி", "traffic", "போக்குவரத்து", "highway"],
    "healthcare": ["மருத்துவ", "hospital", "health", "PHC", "doctor", "மருந்து", "medicine", "ambulance"],
    "education": ["பள்ளி", "school", "college", "கல்வி", "education", "teacher", "ஆசிரியர்", "library"],
    "employment": ["வேலை", "job", "employment", "unemployment", "தொழில்", "factory", "industry"],
    "corruption": ["ஊழல்", "corruption", "bribe", "லஞ்சம்", "scam", "fraud", "misuse"],
    "environment": ["சுற்றுச்சூழல்", "environment", "pollution", "மாசு", "waste", "garbage", "குப்பை"],
    "housing": ["வீடு", "house", "housing", "patta", "பட்டா", "land", "encroachment"],
    "transport": ["பேருந்து", "bus", "train", "ரயில்", "metro", "transport"],
    "sanitation": ["கழிவு", "sewage", "drainage", "toilet", "clean", "sanitation"],
    "agriculture": ["விவசாய", "agriculture", "farmer", "crop", "harvest", "fertilizer", "loan"],
    "law_and_order": ["police", "crime", "காவல்", "murder", "theft", "accident", "விபத்து"],
}


def classify_category(text):
    """Auto-classify article into issue category based on keywords."""
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return "other"


def classify_sentiment(text):
    """Basic sentiment classification based on Tamil/English keyword matching."""
    negative_words = [
        "failure", "failed", "problem", "issue", "protest", "complaint",
        "போராட்டம்", "புகார்", "தோல்வி", "பிரச்சனை", "கண்டனம்",
        "corruption", "ஊழல்", "neglect", "damage", "death", "accident",
        "oppose", "strike", "shortage",
    ]
    positive_words = [
        "inaugurat", "launch", "open", "complet", "success", "benefit",
        "திறப்பு", "வெற்றி", "பயன்", "development", "வளர்ச்சி",
        "improve", "new scheme", "welfare", "award", "achievement",
    ]
    text_lower = text.lower()
    neg_score = sum(1 for w in negative_words if w in text_lower)
    pos_score = sum(1 for w in positive_words if w in text_lower)

    if neg_score > pos_score:
        return "negative"
    elif pos_score > neg_score:
        return "positive"
    return "neutral"


def scrape_dinamani(session):
    """Scrape Dinamani for constituency-related news."""
    articles = []
    base_url = "https://www.dinamani.com"

    for term in [CONSTITUENCY_TAMIL, DISTRICT_TAMIL]:
        search_url = f"{base_url}/search?q={quote_plus(term)}"
        try:
            resp = session.get(search_url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                print(f"  Dinamani search returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for article in soup.select("article, .news-item, .search-result, .story-card")[:10]:
                title_el = article.select_one("h2, h3, .title, a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link_el = article.select_one("a[href]")
                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = base_url + link

                summary_el = article.select_one("p, .summary, .excerpt")
                summary = summary_el.get_text(strip=True) if summary_el else ""

                articles.append({
                    "source": "Dinamani",
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "date": date.today().isoformat(),
                })

            time.sleep(RATE_LIMIT_SECONDS)
        except Exception as e:
            print(f"  Dinamani error: {e}")

    return articles


def scrape_dinathanthi(session):
    """Scrape Dinathanthi for constituency-related news."""
    articles = []
    base_url = "https://www.dailythanthi.com"

    for term in [CONSTITUENCY_TAMIL, DISTRICT_TAMIL]:
        search_url = f"{base_url}/search?q={quote_plus(term)}"
        try:
            resp = session.get(search_url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                print(f"  Dinathanthi search returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for article in soup.select("article, .news-card, .search-result-item, .story")[:10]:
                title_el = article.select_one("h2, h3, .title, a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link_el = article.select_one("a[href]")
                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = base_url + link

                summary_el = article.select_one("p, .desc")
                summary = summary_el.get_text(strip=True) if summary_el else ""

                articles.append({
                    "source": "Dinathanthi",
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "date": date.today().isoformat(),
                })

            time.sleep(RATE_LIMIT_SECONDS)
        except Exception as e:
            print(f"  Dinathanthi error: {e}")

    return articles


def scrape_vikatan(session):
    """Scrape Vikatan for constituency-related news."""
    articles = []
    base_url = "https://www.vikatan.com"

    for term in [CONSTITUENCY_TAMIL, DISTRICT_TAMIL]:
        search_url = f"{base_url}/search?q={quote_plus(term)}"
        try:
            resp = session.get(search_url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                print(f"  Vikatan search returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for article in soup.select("article, .story-card, .search-result, .list-item")[:10]:
                title_el = article.select_one("h2, h3, .title, a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link_el = article.select_one("a[href]")
                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = base_url + link

                summary_el = article.select_one("p, .summary")
                summary = summary_el.get_text(strip=True) if summary_el else ""

                articles.append({
                    "source": "Vikatan",
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "date": date.today().isoformat(),
                })

            time.sleep(RATE_LIMIT_SECONDS)
        except Exception as e:
            print(f"  Vikatan error: {e}")

    return articles


def scrape_thehindu_tamil(session):
    """Scrape The Hindu Tamil for constituency-related news."""
    articles = []
    base_url = "https://www.hindutamil.in"

    for term in [CONSTITUENCY_TAMIL, DISTRICT_TAMIL]:
        search_url = f"{base_url}/search?q={quote_plus(term)}"
        try:
            resp = session.get(search_url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                print(f"  Hindu Tamil search returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for article in soup.select("article, .news-item, .search-result, .card")[:10]:
                title_el = article.select_one("h2, h3, .title, a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link_el = article.select_one("a[href]")
                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = base_url + link

                summary_el = article.select_one("p, .summary")
                summary = summary_el.get_text(strip=True) if summary_el else ""

                articles.append({
                    "source": "The Hindu Tamil",
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "date": date.today().isoformat(),
                })

            time.sleep(RATE_LIMIT_SECONDS)
        except Exception as e:
            print(f"  Hindu Tamil error: {e}")

    return articles


SCRAPERS = {
    "dinamani": scrape_dinamani,
    "dinathanthi": scrape_dinathanthi,
    "vikatan": scrape_vikatan,
    "thehindu": scrape_thehindu_tamil,
}


def store_articles(articles):
    """Store scraped articles in social_sentiment table."""
    conn = get_db()
    c = conn.cursor()

    # Get constituency ID
    c.execute("SELECT id FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
    row = c.fetchone()
    if not row:
        print(f"ERROR: Constituency {CONSTITUENCY} not found in DB. Run seed_data.py first.")
        conn.close()
        return 0

    constituency_id = row["id"]
    stored = 0

    for article in articles:
        combined_text = f"{article['title']} {article.get('summary', '')}"
        sentiment = classify_sentiment(combined_text)
        category = classify_category(combined_text)
        topic_tags = json.dumps([category], ensure_ascii=False)

        # Skip duplicates by URL
        if article.get("url"):
            c.execute("SELECT id FROM social_sentiment WHERE source_url=?", (article["url"],))
            if c.fetchone():
                continue

        c.execute("""
            INSERT INTO social_sentiment (
                constituency_id, platform, content_summary, original_text,
                sentiment, topic_tags, date, source_url, author, language
            ) VALUES (?, 'news', ?, ?, ?, ?, ?, ?, ?, 'tamil')
        """, (
            constituency_id,
            article["title"],
            article.get("summary", ""),
            sentiment,
            topic_tags,
            article.get("date", date.today().isoformat()),
            article.get("url", ""),
            article["source"],
        ))
        stored += 1

    conn.commit()
    conn.close()
    return stored


def import_csv(filepath):
    """Import news data from CSV fallback file.

    Expected CSV columns: source, title, summary, url, date
    """
    articles = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            articles.append({
                "source": row.get("source", "manual"),
                "title": row.get("title", ""),
                "summary": row.get("summary", ""),
                "url": row.get("url", ""),
                "date": row.get("date", date.today().isoformat()),
            })
    return articles


def main():
    parser = argparse.ArgumentParser(description="Scrape Tamil news for constituency intelligence")
    parser.add_argument("--source", choices=list(SCRAPERS.keys()), help="Scrape single source")
    parser.add_argument("--import", dest="import_file", help="Import from CSV file instead of scraping")
    parser.add_argument("--dry-run", action="store_true", help="Print articles without storing")
    args = parser.parse_args()

    if args.import_file:
        print(f"Importing from {args.import_file}...")
        articles = import_csv(args.import_file)
    elif not HAS_SCRAPING:
        print("ERROR: requests and beautifulsoup4 not installed.")
        print("Install with: pip install requests beautifulsoup4")
        print("\nAlternatively, use CSV import:")
        print(f"  python news_scraper.py --import path/to/news.csv")
        print(f"\nCSV format: source,title,summary,url,date")

        # Generate template
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "news_import.csv")
        with open(template_path, "w", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["source", "title", "summary", "url", "date"])
            writer.writerow(["Dinamani", "Sample: திருத்தணி நீர் பிரச்சனை", "Description of the article", "https://example.com/article1", "2026-04-01"])
        print(f"\nTemplate created: {template_path}")
        return
    else:
        print(f"Scraping news for: {CONSTITUENCY} ({CONSTITUENCY_TAMIL})")
        print(f"District: {DISTRICT} ({DISTRICT_TAMIL})")
        print(f"MLA: {MLA_NAME}\n")

        articles = []
        sources = [args.source] if args.source else list(SCRAPERS.keys())
        session = requests.Session()

        for source in sources:
            print(f"Scraping {source}...")
            source_articles = SCRAPERS[source](session)
            print(f"  Found {len(source_articles)} articles")
            articles.extend(source_articles)

    if args.dry_run:
        for a in articles:
            combined = f"{a['title']} {a.get('summary', '')}"
            print(f"\n[{a['source']}] {a['title']}")
            print(f"  Sentiment: {classify_sentiment(combined)}")
            print(f"  Category: {classify_category(combined)}")
            print(f"  URL: {a.get('url', 'N/A')}")
        print(f"\nTotal: {len(articles)} articles (dry run, not stored)")
    else:
        stored = store_articles(articles)
        print(f"\nStored {stored} new articles (skipped duplicates)")


if __name__ == "__main__":
    main()
