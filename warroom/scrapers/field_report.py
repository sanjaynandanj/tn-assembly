"""
Field report input CLI tool.
Enter ground-level intelligence manually: issues, incumbent actions, opposition activities, sentiment.

Usage:
    python field_report.py                    # Interactive CLI
    python field_report.py --import data.csv  # Bulk import from CSV
    python field_report.py --type issue       # Jump to specific report type
"""

import argparse
import csv
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_db

CONSTITUENCY = "TIRUTTANI"

ISSUE_CATEGORIES = [
    "water", "roads", "healthcare", "education", "employment",
    "corruption", "caste", "environment", "housing", "transport",
    "sanitation", "agriculture", "law_and_order", "other",
]

PROMISE_CATEGORIES = [
    "infrastructure", "welfare_scheme", "education", "healthcare",
    "employment", "housing", "water_supply", "agriculture",
    "transport", "environment", "law_and_order", "other",
]


def get_constituency_id(conn):
    c = conn.cursor()
    c.execute("SELECT id FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
    row = c.fetchone()
    if not row:
        print(f"ERROR: Constituency {CONSTITUENCY} not found. Run seed_data.py first.")
        return None
    return row["id"]


def prompt(msg, default=None, choices=None, required=True):
    """Interactive prompt with validation."""
    while True:
        suffix = f" [{default}]" if default else ""
        if choices:
            print(f"\n  Options: {', '.join(choices)}")
        val = input(f"  {msg}{suffix}: ").strip()
        if not val and default:
            return default
        if not val and not required:
            return ""
        if val and choices and val not in choices:
            print(f"  Invalid. Choose from: {', '.join(choices)}")
            continue
        if val or not required:
            return val
        print("  Required field.")


def report_issue(conn, constituency_id):
    """Enter a ground-level issue report."""
    print("\n=== NEW ISSUE REPORT ===")
    print(f"Constituency: {CONSTITUENCY}\n")

    title = prompt("Issue title (brief)")
    description = prompt("Detailed description", required=False)
    category = prompt("Category", choices=ISSUE_CATEGORIES)
    severity = prompt("Severity (1=low, 5=critical)", default="3", choices=["1", "2", "3", "4", "5"])
    source = prompt("Source (your name / informant)", default="field_report")
    affected = prompt("Estimated affected population", required=False)
    status = prompt("Status", default="open", choices=["open", "partially_addressed", "resolved"])

    c = conn.cursor()
    c.execute("""
        INSERT INTO issues (
            constituency_id, category, title, description, severity,
            source, date_reported, affected_population_estimate, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        constituency_id, category, title, description, int(severity),
        source, date.today().isoformat(),
        int(affected) if affected else None, status,
    ))
    conn.commit()
    print(f"\n  Issue #{c.lastrowid} saved.")
    return c.lastrowid


def report_incumbent_action(conn, constituency_id):
    """Enter an incumbent scorecard entry."""
    print("\n=== INCUMBENT SCORECARD ENTRY ===")

    c = conn.cursor()
    c.execute("SELECT current_mla, current_party FROM constituency_profile WHERE id=?", (constituency_id,))
    profile = c.fetchone()
    mla_name = profile["current_mla"]
    party = profile["current_party"]
    print(f"MLA: {mla_name} ({party})\n")

    promise = prompt("Promise / claim made")
    category = prompt("Category", choices=PROMISE_CATEGORIES)
    promise_date = prompt("When was this promised? (YYYY-MM-DD)", default="", required=False)
    promise_source = prompt("Source of promise (speech, manifesto, news)", required=False)
    status = prompt("Delivery status", default="not_started",
                    choices=["not_started", "in_progress", "completed", "failed"])
    evidence = prompt("Evidence / ground reality", required=False)
    evidence_source = prompt("Evidence source", required=False)
    fund_allocated = prompt("Fund allocated (in lakhs, if known)", required=False)
    fund_utilized = prompt("Fund utilized (in lakhs, if known)", required=False)

    c.execute("""
        INSERT INTO incumbent_scorecard (
            constituency_id, mla_name, party, promise_made, promise_category,
            promise_date, promise_source, delivery_status,
            evidence, evidence_source, fund_allocated, fund_utilized
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        constituency_id, mla_name, party, promise, category,
        promise_date or None, promise_source, status,
        evidence, evidence_source,
        float(fund_allocated) if fund_allocated else None,
        float(fund_utilized) if fund_utilized else None,
    ))
    conn.commit()
    print(f"\n  Scorecard entry #{c.lastrowid} saved.")
    return c.lastrowid


def report_opposition_activity(conn, constituency_id):
    """Enter opposition candidate activity."""
    print("\n=== OPPOSITION CANDIDATE ACTIVITY ===")

    # Show known opposition candidates
    c = conn.cursor()
    c.execute("""
        SELECT candidate_name, party, alliance FROM opposition_candidate
        WHERE constituency_id=?
    """, (constituency_id,))
    existing = c.fetchall()
    if existing:
        print("Known opposition candidates:")
        for row in existing:
            print(f"  - {row['candidate_name']} ({row['party']}, {row['alliance']})")

    candidate_name = prompt("Candidate name")
    party = prompt("Party")
    work_done = prompt("Activity / work done")
    work_category = prompt("Category (social_service, rally, charity, media, ground_work, other)",
                          default="ground_work")
    evidence = prompt("Evidence (photo link, witness, etc.)", required=False)
    evidence_source = prompt("Evidence source", required=False)
    activity_date = prompt("Date (YYYY-MM-DD)", default=date.today().isoformat())

    # Check if candidate already exists
    c.execute("""
        SELECT id FROM opposition_candidate
        WHERE constituency_id=? AND candidate_name=? AND party=?
    """, (constituency_id, candidate_name, party))
    existing_row = c.fetchone()

    if existing_row:
        # Append to existing work_done
        c.execute("""
            UPDATE opposition_candidate SET
                work_done = COALESCE(work_done, '') || char(10) || ?,
                evidence = COALESCE(evidence, '') || char(10) || ?,
                date = ?
            WHERE id = ?
        """, (
            f"[{activity_date}] {work_done}",
            evidence or "",
            activity_date,
            existing_row["id"],
        ))
        print(f"\n  Updated candidate #{existing_row['id']}")
    else:
        c.execute("""
            INSERT INTO opposition_candidate (
                constituency_id, candidate_name, party, work_done,
                work_category, evidence, evidence_source, date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            constituency_id, candidate_name, party,
            f"[{activity_date}] {work_done}",
            work_category, evidence, evidence_source, activity_date,
        ))
        print(f"\n  New opposition entry #{c.lastrowid} saved.")

    conn.commit()


def report_sentiment(conn, constituency_id):
    """Enter a general sentiment observation."""
    print("\n=== SENTIMENT OBSERVATION ===")

    platform = prompt("Source", default="field_report",
                     choices=["field_report", "whatsapp", "facebook", "twitter", "youtube", "other"])
    summary = prompt("What did you observe? (brief)")
    detail = prompt("Details / quotes (optional)", required=False)
    sentiment = prompt("Overall sentiment", choices=["positive", "negative", "neutral", "mixed"])
    topic = prompt("Main topic (water, roads, healthcare, employment, caste, election, other)",
                  default="other")
    source_person = prompt("Who said this / source", default="anonymous")
    obs_date = prompt("Date", default=date.today().isoformat())

    c = conn.cursor()
    topic_tags = json.dumps([topic], ensure_ascii=False)

    c.execute("""
        INSERT INTO social_sentiment (
            constituency_id, platform, content_summary, original_text,
            sentiment, topic_tags, date, author, language
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'tamil')
    """, (
        constituency_id, platform, summary, detail or summary,
        sentiment, topic_tags, obs_date, source_person,
    ))
    conn.commit()
    print(f"\n  Sentiment entry #{c.lastrowid} saved.")


def bulk_import(filepath, report_type):
    """Import field reports from CSV.

    CSV columns depend on report_type:
    - issue: title,description,category,severity,source,affected_population,status
    - scorecard: promise_made,promise_category,delivery_status,evidence,fund_allocated,fund_utilized
    - sentiment: platform,summary,detail,sentiment,topic,source_person,date
    """
    conn = get_db()
    constituency_id = get_constituency_id(conn)
    if not constituency_id:
        return

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        c = conn.cursor()

        for row in reader:
            if report_type == "issue":
                c.execute("""
                    INSERT INTO issues (
                        constituency_id, category, title, description, severity,
                        source, date_reported, affected_population_estimate, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    constituency_id,
                    row.get("category", "other"),
                    row["title"],
                    row.get("description", ""),
                    int(row.get("severity", 3)),
                    row.get("source", "csv_import"),
                    row.get("date", date.today().isoformat()),
                    int(row["affected_population"]) if row.get("affected_population") else None,
                    row.get("status", "open"),
                ))
            elif report_type == "scorecard":
                profile = c.execute("SELECT current_mla, current_party FROM constituency_profile WHERE id=?",
                                   (constituency_id,)).fetchone()
                c.execute("""
                    INSERT INTO incumbent_scorecard (
                        constituency_id, mla_name, party, promise_made, promise_category,
                        delivery_status, evidence, fund_allocated, fund_utilized
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    constituency_id, profile["current_mla"], profile["current_party"],
                    row["promise_made"],
                    row.get("promise_category", "other"),
                    row.get("delivery_status", "not_started"),
                    row.get("evidence", ""),
                    float(row["fund_allocated"]) if row.get("fund_allocated") else None,
                    float(row["fund_utilized"]) if row.get("fund_utilized") else None,
                ))
            elif report_type == "sentiment":
                topic_tags = json.dumps([row.get("topic", "other")], ensure_ascii=False)
                c.execute("""
                    INSERT INTO social_sentiment (
                        constituency_id, platform, content_summary, original_text,
                        sentiment, topic_tags, date, author, language
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'tamil')
                """, (
                    constituency_id,
                    row.get("platform", "field_report"),
                    row.get("summary", ""),
                    row.get("detail", row.get("summary", "")),
                    row.get("sentiment", "neutral"),
                    topic_tags,
                    row.get("date", date.today().isoformat()),
                    row.get("source_person", "csv_import"),
                ))
            count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} {report_type} records")


def generate_templates():
    """Generate CSV templates for bulk import."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    os.makedirs(template_dir, exist_ok=True)

    # Issues template
    with open(os.path.join(template_dir, "issues_import.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "description", "category", "severity", "source", "date", "affected_population", "status"])
        w.writerow(["Drinking water shortage in ward 5", "Bore wells dried up, tanker supply irregular",
                    "water", "4", "field_visit", "2026-04-01", "5000", "open"])

    # Scorecard template
    with open(os.path.join(template_dir, "scorecard_import.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["promise_made", "promise_category", "delivery_status", "evidence", "fund_allocated", "fund_utilized"])
        w.writerow(["New bus stand construction", "transport", "in_progress",
                    "Foundation laid but work stalled since 6 months", "150", "45"])

    # Sentiment template
    with open(os.path.join(template_dir, "sentiment_import.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["platform", "summary", "detail", "sentiment", "topic", "source_person", "date"])
        w.writerow(["field_report", "Youth frustrated with unemployment",
                    "Multiple youth groups expressing frustration about lack of jobs",
                    "negative", "employment", "local contact", "2026-04-01"])

    print(f"Templates created in {template_dir}/")
    print("  - issues_import.csv")
    print("  - scorecard_import.csv")
    print("  - sentiment_import.csv")


def interactive_menu(conn, constituency_id):
    """Main interactive CLI menu."""
    print(f"\n{'='*50}")
    print(f"  FIELD REPORT INPUT — {CONSTITUENCY}")
    print(f"{'='*50}")

    while True:
        print(f"\n  1. Report an ISSUE")
        print(f"  2. Record INCUMBENT action/promise")
        print(f"  3. Record OPPOSITION activity")
        print(f"  4. Record SENTIMENT observation")
        print(f"  5. Generate CSV templates")
        print(f"  6. Show database summary")
        print(f"  q. Quit")

        choice = input("\n  Enter choice: ").strip().lower()

        if choice == "1":
            report_issue(conn, constituency_id)
        elif choice == "2":
            report_incumbent_action(conn, constituency_id)
        elif choice == "3":
            report_opposition_activity(conn, constituency_id)
        elif choice == "4":
            report_sentiment(conn, constituency_id)
        elif choice == "5":
            generate_templates()
        elif choice == "6":
            show_summary(conn, constituency_id)
        elif choice in ("q", "quit", "exit"):
            print("Done.")
            break


def show_summary(conn, constituency_id):
    """Show database entry counts."""
    c = conn.cursor()
    tables = [
        ("Issues", "issues"),
        ("Scorecard entries", "incumbent_scorecard"),
        ("Opposition entries", "opposition_candidate"),
        ("Sentiment entries", "social_sentiment"),
        ("Content outputs", "content_output"),
    ]
    print(f"\n--- Database Summary ---")
    for label, table in tables:
        c.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE constituency_id=?", (constituency_id,))
        print(f"  {label}: {c.fetchone()['cnt']}")


def main():
    parser = argparse.ArgumentParser(description="Field report input for constituency intelligence")
    parser.add_argument("--type", choices=["issue", "scorecard", "opposition", "sentiment"],
                       help="Jump directly to specific report type")
    parser.add_argument("--import", dest="import_file", help="Bulk import from CSV")
    parser.add_argument("--import-type", choices=["issue", "scorecard", "sentiment"],
                       help="Type of data in import CSV")
    parser.add_argument("--generate-templates", action="store_true", help="Generate CSV templates")
    args = parser.parse_args()

    if args.generate_templates:
        generate_templates()
        return

    if args.import_file:
        if not args.import_type:
            print("ERROR: Specify --import-type (issue, scorecard, or sentiment)")
            return
        bulk_import(args.import_file, args.import_type)
        return

    conn = get_db()
    constituency_id = get_constituency_id(conn)
    if not constituency_id:
        conn.close()
        return

    if args.type:
        dispatch = {
            "issue": report_issue,
            "scorecard": report_incumbent_action,
            "opposition": report_opposition_activity,
            "sentiment": report_sentiment,
        }
        dispatch[args.type](conn, constituency_id)
    else:
        interactive_menu(conn, constituency_id)

    conn.close()


if __name__ == "__main__":
    main()
