"""
Constituency Intelligence Report Generator.
Produces a comprehensive Markdown report with:
- Top issues by severity and recurrence
- Incumbent performance score
- Sentiment trend analysis
- Opposition candidate strength assessment
- Key narratives from news + social media
- Vulnerabilities to exploit / strengths to counter

Usage:
    python intelligence_report.py                    # Generate full report
    python intelligence_report.py --section issues   # Generate specific section
    python intelligence_report.py --output report.md # Save to file
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_db

CONSTITUENCY = "TIRUTTANI"


def get_profile(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
    return c.fetchone()


def generate_header(profile):
    lines = []
    lines.append(f"# INTELLIGENCE REPORT: {profile['name']}")
    lines.append(f"**District:** {profile['district']} | **AC No:** {profile['ac_no']} | "
                 f"**Type:** {profile['constituency_type']}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Profile summary
    lines.append("## 1. Constituency Profile")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Current MLA | **{profile['current_mla']}** ({profile['current_party']}) |")
    lines.append(f"| Sub-Region | {profile['sub_region']} |")
    lines.append(f"| Voters (2021) | {profile['voter_count']:,} |")
    if profile['voter_count_2026']:
        lines.append(f"| Voters (2026 est.) | {profile['voter_count_2026']:,} |")
        change = profile['voter_count_2026'] - profile['voter_count']
        change_pct = (change / profile['voter_count'] * 100)
        lines.append(f"| Voter Change | {change:+,} ({change_pct:+.1f}%) |")
    lines.append(f"| 2021 Margin | {profile['last_election_margin']:,} ({profile['last_election_margin_pct']}%) |")
    lines.append(f"| 2021 Turnout | {profile['last_election_turnout']}% |")
    lines.append(f"| Effective No. of Parties | {profile['enop']} |")
    lines.append(f"| Runner-up | {profile['runner_up_candidate']} ({profile['runner_up_party']}) |")
    if profile['electors_male'] and profile['electors_female']:
        total = profile['electors_male'] + profile['electors_female'] + (profile['electors_third_gender'] or 0)
        lines.append(f"| Male Voters | {profile['electors_male']:,} ({profile['electors_male']/total*100:.1f}%) |")
        lines.append(f"| Female Voters | {profile['electors_female']:,} ({profile['electors_female']/total*100:.1f}%) |")
    lines.append("")
    return "\n".join(lines)


def generate_2021_results(conn, profile):
    c = conn.cursor()
    c.execute("""
        SELECT * FROM candidate_2021 WHERE constituency_id=?
        ORDER BY position ASC
    """, (profile['id'],))
    candidates = c.fetchall()

    lines = []
    lines.append("## 2. 2021 Election Results")
    lines.append("")
    lines.append("| Pos | Candidate | Party | Votes | Vote Share | Deposit Lost |")
    lines.append("|-----|-----------|-------|------:|------------|:------------:|")

    for cand in candidates:
        deposit = "Yes" if cand['deposit_lost'] == 'yes' else "No"
        lines.append(
            f"| {cand['position']} | {cand['candidate_name']} | {cand['party']} | "
            f"{cand['votes']:,} | {cand['vote_share_pct']:.1f}% | {deposit} |"
        )

    lines.append("")
    return "\n".join(lines)


def generate_2026_candidates(conn, profile):
    c = conn.cursor()
    c.execute("""
        SELECT * FROM candidate_2026 WHERE constituency_id=?
    """, (profile['id'],))
    candidates = c.fetchall()

    if not candidates:
        return ""

    lines = []
    lines.append("## 3. 2026 Declared Candidates")
    lines.append("")
    lines.append("| Candidate | Party | Alliance |")
    lines.append("|-----------|-------|----------|")

    for cand in candidates:
        lines.append(f"| {cand['candidate_name']} | {cand['party']} | {cand['alliance']} |")

    lines.append("")
    return "\n".join(lines)


def generate_issues_analysis(conn, profile):
    c = conn.cursor()
    c.execute("""
        SELECT * FROM issues WHERE constituency_id=?
        ORDER BY severity DESC, date_reported DESC
    """, (profile['id'],))
    issues = c.fetchall()

    lines = []
    lines.append("## 4. Issues Analysis")
    lines.append("")

    if not issues:
        lines.append("*No issues recorded yet. Use field_report.py to add ground-level issues.*")
        lines.append("")
        return "\n".join(lines)

    # Category breakdown
    category_counts = Counter(i['category'] for i in issues)
    severity_sum = {}
    for issue in issues:
        cat = issue['category']
        severity_sum[cat] = severity_sum.get(cat, 0) + issue['severity']

    lines.append("### Top Issues by Category")
    lines.append("")
    lines.append("| Category | Count | Avg Severity | Status |")
    lines.append("|----------|------:|:------------:|--------|")

    for cat, count in category_counts.most_common():
        avg_sev = severity_sum[cat] / count
        status_counts = Counter(i['status'] for i in issues if i['category'] == cat)
        status_str = ", ".join(f"{s}: {c}" for s, c in status_counts.items())
        sev_bar = "🔴" if avg_sev >= 4 else "🟡" if avg_sev >= 3 else "🟢"
        lines.append(f"| {cat} | {count} | {avg_sev:.1f} {sev_bar} | {status_str} |")

    # Top 5 most severe issues
    lines.append("")
    lines.append("### Top 5 Critical Issues")
    lines.append("")
    for i, issue in enumerate(issues[:5], 1):
        verified = " [VERIFIED]" if issue['verified'] else ""
        lines.append(f"**{i}. {issue['title']}** (Severity: {issue['severity']}/5){verified}")
        if issue['description']:
            lines.append(f"   {issue['description']}")
        lines.append(f"   Category: {issue['category']} | Status: {issue['status']} | "
                     f"Reported: {issue['date_reported']}")
        if issue['affected_population_estimate']:
            lines.append(f"   Affected population: ~{issue['affected_population_estimate']:,}")
        lines.append("")

    return "\n".join(lines)


def generate_incumbent_scorecard(conn, profile):
    c = conn.cursor()
    c.execute("""
        SELECT * FROM incumbent_scorecard WHERE constituency_id=?
        ORDER BY delivery_status, promise_category
    """, (profile['id'],))
    entries = c.fetchall()

    lines = []
    lines.append("## 5. Incumbent Scorecard")
    lines.append(f"**MLA: {profile['current_mla']}** ({profile['current_party']})")
    lines.append("")

    if not entries:
        lines.append("*No scorecard entries yet. Use field_report.py or govt_data_parser.py to add data.*")
        lines.append("")
        return "\n".join(lines)

    # Summary stats
    total = len(entries)
    status_counts = Counter(e['delivery_status'] for e in entries)
    completed = status_counts.get('completed', 0)
    failed = status_counts.get('failed', 0)
    in_progress = status_counts.get('in_progress', 0)
    not_started = status_counts.get('not_started', 0)

    score = 0
    if total > 0:
        score = ((completed * 1.0 + in_progress * 0.5) / total) * 100

    total_allocated = sum(e['fund_allocated'] or 0 for e in entries)
    total_utilized = sum(e['fund_utilized'] or 0 for e in entries)
    utilization_pct = (total_utilized / total_allocated * 100) if total_allocated > 0 else 0

    lines.append("### Performance Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Overall Score | **{score:.0f}/100** |")
    lines.append(f"| Promises Completed | {completed}/{total} |")
    lines.append(f"| Promises Failed | {failed}/{total} |")
    lines.append(f"| In Progress | {in_progress}/{total} |")
    lines.append(f"| Not Started | {not_started}/{total} |")
    if total_allocated > 0:
        lines.append(f"| Funds Allocated | ₹{total_allocated:.1f} lakhs |")
        lines.append(f"| Funds Utilized | ₹{total_utilized:.1f} lakhs ({utilization_pct:.0f}%) |")
    lines.append("")

    # Detailed entries
    lines.append("### Promise Details")
    lines.append("")
    status_emoji = {"completed": "✅", "in_progress": "🔄", "not_started": "⏳", "failed": "❌"}

    for entry in entries:
        emoji = status_emoji.get(entry['delivery_status'], "❓")
        lines.append(f"- {emoji} **{entry['promise_made'][:100]}**")
        lines.append(f"  Status: {entry['delivery_status']}")
        if entry['evidence']:
            lines.append(f"  Evidence: {entry['evidence']}")
        if entry['fund_allocated']:
            fund_str = f"  Funds: ₹{entry['fund_allocated']:.1f}L allocated"
            if entry['fund_utilized']:
                fund_str += f", ₹{entry['fund_utilized']:.1f}L utilized"
            lines.append(fund_str)
        lines.append("")

    return "\n".join(lines)


def generate_sentiment_analysis(conn, profile):
    c = conn.cursor()
    c.execute("""
        SELECT * FROM social_sentiment WHERE constituency_id=?
        ORDER BY date DESC
    """, (profile['id'],))
    entries = c.fetchall()

    lines = []
    lines.append("## 6. Sentiment Analysis")
    lines.append("")

    if not entries:
        lines.append("*No sentiment data yet. Use scrapers or field_report.py to add entries.*")
        lines.append("")
        return "\n".join(lines)

    # Overall sentiment breakdown
    sentiment_counts = Counter(e['sentiment'] for e in entries)
    total = len(entries)

    lines.append("### Overall Sentiment")
    lines.append("")
    for sent in ['positive', 'negative', 'neutral', 'mixed']:
        count = sentiment_counts.get(sent, 0)
        pct = count / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(f"  {sent:10s} {bar} {count} ({pct:.0f}%)")
    lines.append("")

    # Platform breakdown
    platform_counts = Counter(e['platform'] for e in entries)
    lines.append("### By Platform")
    lines.append("")
    lines.append("| Platform | Count | Positive | Negative | Neutral |")
    lines.append("|----------|------:|---------:|---------:|--------:|")

    for platform, count in platform_counts.most_common():
        pos = sum(1 for e in entries if e['platform'] == platform and e['sentiment'] == 'positive')
        neg = sum(1 for e in entries if e['platform'] == platform and e['sentiment'] == 'negative')
        neu = sum(1 for e in entries if e['platform'] == platform and e['sentiment'] == 'neutral')
        lines.append(f"| {platform} | {count} | {pos} | {neg} | {neu} |")
    lines.append("")

    # Topic breakdown
    all_topics = []
    for e in entries:
        try:
            tags = json.loads(e['topic_tags']) if e['topic_tags'] else []
            all_topics.extend(t for t in tags if not t.startswith("engagement:"))
        except (json.JSONDecodeError, TypeError):
            pass

    if all_topics:
        topic_counts = Counter(all_topics)
        lines.append("### Key Topics")
        lines.append("")
        for topic, count in topic_counts.most_common(10):
            lines.append(f"  - **{topic}**: {count} mentions")
        lines.append("")

    # Recent entries
    lines.append("### Recent Entries (last 10)")
    lines.append("")
    for entry in entries[:10]:
        sent_emoji = {"positive": "🟢", "negative": "🔴", "neutral": "⚪", "mixed": "🟡"}.get(entry['sentiment'], "⚪")
        lines.append(f"- {sent_emoji} [{entry['platform']}] {entry['content_summary'][:120]}")
        lines.append(f"  Date: {entry['date']} | Author: {entry['author'] or 'N/A'}")
        lines.append("")

    return "\n".join(lines)


def generate_opposition_assessment(conn, profile):
    c = conn.cursor()
    c.execute("""
        SELECT * FROM opposition_candidate WHERE constituency_id=?
    """, (profile['id'],))
    candidates = c.fetchall()

    lines = []
    lines.append("## 7. Opposition Assessment")
    lines.append("")

    if not candidates:
        lines.append("*No opposition data yet. Use field_report.py to record opposition activities.*")
        lines.append("")
        return "\n".join(lines)

    for cand in candidates:
        alliance_str = f", {cand['alliance']}" if cand['alliance'] else ""
        lines.append(f"### {cand['candidate_name']} ({cand['party']}{alliance_str})")
        lines.append("")

        if cand['work_done']:
            lines.append("**Activities:**")
            for line in cand['work_done'].split("\n"):
                if line.strip():
                    lines.append(f"  - {line.strip()}")
            lines.append("")

        if cand['strengths']:
            try:
                strengths = json.loads(cand['strengths'])
                lines.append("**Strengths:**")
                for s in strengths:
                    lines.append(f"  - {s}")
                lines.append("")
            except (json.JSONDecodeError, TypeError):
                pass

        if cand['vulnerabilities']:
            try:
                vulns = json.loads(cand['vulnerabilities'])
                lines.append("**Vulnerabilities:**")
                for v in vulns:
                    lines.append(f"  - {v}")
                lines.append("")
            except (json.JSONDecodeError, TypeError):
                pass

    return "\n".join(lines)


def generate_strategic_summary(conn, profile):
    """Generate the strategic vulnerabilities and strengths section."""
    c = conn.cursor()

    lines = []
    lines.append("## 8. Strategic Assessment")
    lines.append("")

    # Vulnerabilities (things to exploit against incumbent)
    lines.append("### Vulnerabilities (Attack Vectors)")
    lines.append("")

    # Check for failed promises
    c.execute("""
        SELECT COUNT(*) as cnt FROM incumbent_scorecard
        WHERE constituency_id=? AND delivery_status='failed'
    """, (profile['id'],))
    failed = c.fetchone()['cnt']
    if failed:
        lines.append(f"- **{failed} failed promises** — direct attack material with evidence")

    # Check for low fund utilization
    c.execute("""
        SELECT SUM(fund_allocated) as alloc, SUM(fund_utilized) as util
        FROM incumbent_scorecard WHERE constituency_id=?
    """, (profile['id'],))
    funds = c.fetchone()
    if funds['alloc'] and funds['alloc'] > 0:
        util_pct = (funds['util'] or 0) / funds['alloc'] * 100
        if util_pct < 60:
            lines.append(f"- **Low fund utilization ({util_pct:.0f}%)** — "
                         f"₹{funds['alloc'] - (funds['util'] or 0):.1f}L unspent")

    # Check severe unresolved issues
    c.execute("""
        SELECT COUNT(*) as cnt FROM issues
        WHERE constituency_id=? AND severity >= 4 AND status='open'
    """, (profile['id'],))
    severe = c.fetchone()['cnt']
    if severe:
        lines.append(f"- **{severe} critical unresolved issues** (severity 4-5)")

    # Negative sentiment trend
    c.execute("""
        SELECT sentiment, COUNT(*) as cnt FROM social_sentiment
        WHERE constituency_id=? GROUP BY sentiment
    """, (profile['id'],))
    sentiments = {r['sentiment']: r['cnt'] for r in c.fetchall()}
    neg = sentiments.get('negative', 0)
    total_sent = sum(sentiments.values())
    if total_sent > 0 and neg / total_sent > 0.4:
        lines.append(f"- **High negative sentiment ({neg}/{total_sent}, {neg/total_sent*100:.0f}%)** — "
                     f"public mood is against incumbent")

    # Margin analysis
    if profile['last_election_margin_pct'] and profile['last_election_margin_pct'] < 10:
        lines.append(f"- **Tight 2021 margin ({profile['last_election_margin_pct']}%)** — "
                     f"constituency is winnable with swing of {profile['last_election_margin_pct']/2:.1f}%")

    if not failed and not severe and total_sent == 0:
        lines.append("- *Insufficient data — add more field reports and scorecard entries*")

    lines.append("")

    # Strengths to counter (what incumbent will claim)
    lines.append("### Incumbent Strengths to Counter")
    lines.append("")

    c.execute("""
        SELECT COUNT(*) as cnt FROM incumbent_scorecard
        WHERE constituency_id=? AND delivery_status='completed'
    """, (profile['id'],))
    completed = c.fetchone()['cnt']
    if completed:
        lines.append(f"- **{completed} completed promises** — incumbent will use these; "
                     f"prepare counter-narratives on quality/impact")

    if profile['last_election_margin_pct'] and profile['last_election_margin_pct'] > 15:
        lines.append(f"- **Strong 2021 mandate ({profile['last_election_margin_pct']}%)** — "
                     f"incumbent has comfort; needs significant anti-incumbency to overcome")

    pos = sentiments.get('positive', 0)
    if total_sent > 0 and pos / total_sent > 0.4:
        lines.append(f"- **Positive public sentiment ({pos/total_sent*100:.0f}%)** — "
                     f"incumbent is seen favorably; attack must be specific and evidence-based")

    if not completed and profile['last_election_margin_pct'] and profile['last_election_margin_pct'] <= 15:
        lines.append("- *No strong incumbent advantages detected based on current data*")

    lines.append("")
    return "\n".join(lines)


def generate_full_report(conn):
    profile = get_profile(conn)
    if not profile:
        return f"ERROR: Constituency {CONSTITUENCY} not found in database."

    sections = [
        generate_header(profile),
        generate_2021_results(conn, profile),
        generate_2026_candidates(conn, profile),
        generate_issues_analysis(conn, profile),
        generate_incumbent_scorecard(conn, profile),
        generate_sentiment_analysis(conn, profile),
        generate_opposition_assessment(conn, profile),
        generate_strategic_summary(conn, profile),
    ]

    report = "\n".join(sections)
    report += "\n---\n*Report generated by Warroom Intelligence System*\n"
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate constituency intelligence report")
    parser.add_argument("--output", "-o", help="Save report to file")
    parser.add_argument("--section", choices=[
        "profile", "results", "candidates", "issues",
        "scorecard", "sentiment", "opposition", "strategy"
    ], help="Generate specific section only")
    args = parser.parse_args()

    conn = get_db()
    report = generate_full_report(conn)
    conn.close()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
