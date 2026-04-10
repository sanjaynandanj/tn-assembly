"""
Twitter/X search and sentiment capture for constituency intelligence.

Since X API access requires paid tier, this provides:
1. A structured CSV template for manual tweet capture
2. CSV import into social_sentiment table
3. Auto-classification of sentiment and topics
4. Optional API integration if credentials are available

Usage:
    python twitter_search.py --generate-template   # Create blank CSV template
    python twitter_search.py --import tweets.csv    # Import from CSV
    python twitter_search.py --search               # Search via API (needs .env)
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_db

# Reuse classifiers from news scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_scraper import classify_sentiment, classify_category

CONSTITUENCY = "TIRUTTANI"
CONSTITUENCY_TAMIL = "திருத்தணி"
DISTRICT_TAMIL = "திருவள்ளூர்"
MLA_NAME = "S.Chandran"

SEARCH_QUERIES = [
    f"{CONSTITUENCY_TAMIL} OR Tiruttani",
    f"{DISTRICT_TAMIL} constituency",
    f"திருத்தணி MLA OR சட்டமன்ற உறுப்பினர்",
    f"Tiruttani election 2026",
    f"திருத்தணி தொகுதி",
]

TEMPLATE_HEADERS = [
    "tweet_text",
    "author_handle",
    "author_name",
    "date",
    "tweet_url",
    "likes",
    "retweets",
    "replies",
    "language",
    "media_type",
]


def generate_template():
    """Generate a blank CSV template for manual tweet data entry."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    os.makedirs(template_dir, exist_ok=True)
    template_path = os.path.join(template_dir, "twitter_import.csv")

    with open(template_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(TEMPLATE_HEADERS)
        # Sample rows
        writer.writerow([
            "திருத்தணி சாலை மோசமான நிலையில் உள்ளது. எம்எல்ஏ என்ன செய்கிறார்?",
            "@sample_user",
            "Sample User",
            "2026-04-01",
            "https://x.com/sample_user/status/123456",
            "45",
            "12",
            "8",
            "tamil",
            "image",
        ])
        writer.writerow([
            "Tiruttani new bus stand inauguration - good work by DMK govt",
            "@another_user",
            "Another User",
            "2026-04-02",
            "https://x.com/another_user/status/789012",
            "120",
            "30",
            "15",
            "english",
            "",
        ])

    print(f"Template created: {template_path}")
    print(f"\nColumns: {', '.join(TEMPLATE_HEADERS)}")
    print(f"\nSearch queries to use on X:")
    for q in SEARCH_QUERIES:
        print(f"  - {q}")
    print(f"\nInstructions:")
    print(f"  1. Search X with the queries above")
    print(f"  2. Copy relevant tweet data into the CSV")
    print(f"  3. Run: python twitter_search.py --import templates/twitter_import.csv")
    return template_path


def import_csv(filepath):
    """Import tweet data from CSV into social_sentiment table."""
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
    row = c.fetchone()
    if not row:
        print(f"ERROR: Constituency {CONSTITUENCY} not found. Run seed_data.py first.")
        conn.close()
        return

    constituency_id = row["id"]
    stored = 0
    skipped = 0

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tweet_text = row.get("tweet_text", "").strip()
            if not tweet_text:
                continue

            tweet_url = row.get("tweet_url", "").strip()

            # Skip duplicates
            if tweet_url:
                c.execute("SELECT id FROM social_sentiment WHERE source_url=?", (tweet_url,))
                if c.fetchone():
                    skipped += 1
                    continue

            sentiment = classify_sentiment(tweet_text)
            category = classify_category(tweet_text)

            engagement = {}
            for field in ["likes", "retweets", "replies"]:
                val = row.get(field, "").strip()
                if val:
                    engagement[field] = int(val)

            topic_tags = json.dumps([category], ensure_ascii=False)
            if engagement:
                topic_tags = json.dumps([category, f"engagement:{sum(engagement.values())}"], ensure_ascii=False)

            c.execute("""
                INSERT INTO social_sentiment (
                    constituency_id, platform, content_summary, original_text,
                    sentiment, topic_tags, date, source_url, author, language
                ) VALUES (?, 'twitter', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                constituency_id,
                tweet_text[:200],  # Summary is truncated
                tweet_text,
                sentiment,
                topic_tags,
                row.get("date", date.today().isoformat()),
                tweet_url,
                row.get("author_handle", ""),
                row.get("language", "tamil"),
            ))
            stored += 1

    conn.commit()
    conn.close()
    print(f"Stored {stored} tweets, skipped {skipped} duplicates")


def search_api():
    """Search X API (requires TWITTER_BEARER_TOKEN in .env or environment)."""
    token = os.environ.get("TWITTER_BEARER_TOKEN")
    if not token:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("TWITTER_BEARER_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not token:
        print("ERROR: No X API token found.")
        print("Set TWITTER_BEARER_TOKEN in environment or .env file.")
        print("\nFallback: Use manual CSV import instead:")
        print("  python twitter_search.py --generate-template")
        return

    try:
        import requests
    except ImportError:
        print("ERROR: requests library not installed. pip install requests")
        return

    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.twitter.com/2/tweets/search/recent"

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
    row = c.fetchone()
    if not row:
        print(f"ERROR: Constituency {CONSTITUENCY} not found.")
        conn.close()
        return
    constituency_id = row["id"]

    total_stored = 0
    for query in SEARCH_QUERIES[:3]:  # Limit queries to avoid rate limits
        params = {
            "query": query,
            "max_results": 50,
            "tweet.fields": "created_at,public_metrics,lang,author_id",
        }

        try:
            resp = requests.get(base_url, headers=headers, params=params, timeout=15)
            if resp.status_code == 429:
                print("  Rate limited. Try again later.")
                break
            if resp.status_code != 200:
                print(f"  API error {resp.status_code}: {resp.text[:200]}")
                continue

            data = resp.json()
            tweets = data.get("data", [])
            print(f"  Query '{query[:40]}...' returned {len(tweets)} tweets")

            for tweet in tweets:
                text = tweet["text"]
                tweet_id = tweet["id"]
                tweet_url = f"https://x.com/i/status/{tweet_id}"

                # Skip duplicates
                c.execute("SELECT id FROM social_sentiment WHERE source_url=?", (tweet_url,))
                if c.fetchone():
                    continue

                sentiment = classify_sentiment(text)
                category = classify_category(text)
                metrics = tweet.get("public_metrics", {})
                engagement = metrics.get("like_count", 0) + metrics.get("retweet_count", 0)

                topic_tags = json.dumps([category, f"engagement:{engagement}"], ensure_ascii=False)

                c.execute("""
                    INSERT INTO social_sentiment (
                        constituency_id, platform, content_summary, original_text,
                        sentiment, topic_tags, date, source_url, author, language
                    ) VALUES (?, 'twitter', ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    constituency_id,
                    text[:200],
                    text,
                    sentiment,
                    topic_tags,
                    tweet.get("created_at", "")[:10],
                    tweet_url,
                    str(tweet.get("author_id", "")),
                    tweet.get("lang", "und"),
                ))
                total_stored += 1

        except Exception as e:
            print(f"  Error: {e}")

    conn.commit()
    conn.close()
    print(f"\nTotal stored: {total_stored} tweets")


def main():
    parser = argparse.ArgumentParser(description="Twitter/X search for constituency intelligence")
    parser.add_argument("--generate-template", action="store_true", help="Generate blank CSV template")
    parser.add_argument("--import", dest="import_file", help="Import from CSV file")
    parser.add_argument("--search", action="store_true", help="Search via X API")
    args = parser.parse_args()

    if args.generate_template:
        generate_template()
    elif args.import_file:
        import_csv(args.import_file)
    elif args.search:
        search_api()
    else:
        print("Choose an action:")
        print("  --generate-template  Create CSV template for manual data entry")
        print("  --import FILE        Import tweet data from CSV")
        print("  --search             Search via X API (needs bearer token)")


if __name__ == "__main__":
    main()
