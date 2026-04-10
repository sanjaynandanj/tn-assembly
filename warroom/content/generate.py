"""
Content generation engine using Claude API.
Generates campaign-ready content grounded in database evidence.

Every generated piece references specific source data (issue IDs, scorecard entries).
Content flagged as NEEDS_VERIFICATION when evidence is weak.

Usage:
    python generate.py --type social_post --issue 1        # Generate from an issue
    python generate.py --type whatsapp_forward --issue 1,2  # Multiple issues
    python generate.py --type video_script --scorecard 1    # Generate from scorecard
    python generate.py --type talking_point --all           # All issues + scorecard
    python generate.py --type counter_narrative --claim "..."  # Counter a specific claim
    python generate.py --tone aggressive_attack             # Set tone
    python generate.py --list-sources                       # Show available source data
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_db

try:
    import anthropic
    HAS_API = True
except ImportError:
    HAS_API = False

CONSTITUENCY = "TIRUTTANI"

CONTENT_TYPES = {
    "social_post": {
        "description": "Tamil social media post (Twitter/Facebook/Instagram)",
        "max_length": "280 chars for Twitter, 500 for Facebook",
        "instruction": """Generate a sharp, impactful Tamil social media post.
Include 2-3 relevant hashtags in Tamil.
Must be factual and reference specific data points.
Create both Tamil and English versions.
Keep it punchy and shareable.""",
    },
    "whatsapp_forward": {
        "description": "WhatsApp forward message (Tamil, punchy, shareable)",
        "max_length": "300-500 words",
        "instruction": """Generate a WhatsApp forward message in Tamil.
Use emojis strategically for visual impact.
Structure: Hook line → Key facts → Emotional appeal → Call to action.
Must be easy to read and forward.
Include both Tamil and English versions.
End with a shareable one-liner.""",
    },
    "video_script": {
        "description": "Short video script (30-60 seconds, Tamil)",
        "max_length": "150-200 words (spoken)",
        "instruction": """Write a 30-60 second video script in Tamil.
Structure: Opening hook (5 sec) → Problem statement with data (15 sec) →
Emotional middle (15 sec) → Call to action (10 sec).
Include visual cues in [brackets].
Both Tamil and English versions.
Tone should match the requested style.""",
    },
    "talking_point": {
        "description": "Structured talking points with evidence citations",
        "max_length": "bullet points",
        "instruction": """Generate structured talking points for a candidate.
Each point must include:
- The claim/statement
- Supporting evidence with source reference
- Suggested delivery (when/where to use this)
- Potential counter-argument and response
Both Tamil and English versions.""",
    },
    "counter_narrative": {
        "description": "Rebuttal to incumbent claims with data",
        "max_length": "varies",
        "instruction": """Generate a counter-narrative to rebut a specific claim.
Structure:
- The claim being made
- Why it's misleading/false (with data)
- The reality (with evidence)
- A punchy one-liner rebuttal
Both Tamil and English versions.""",
    },
    "infographic_text": {
        "description": "Text content for infographic design",
        "max_length": "headline + 5-7 data points",
        "instruction": """Generate text content for an infographic.
Include:
- Headline (punchy, Tamil)
- 5-7 key data points with numbers
- Source attribution
- Bottom line / takeaway
Both Tamil and English versions.""",
    },
}

TONE_INSTRUCTIONS = {
    "aggressive_attack": "Be hard-hitting and confrontational. Use strong language to expose failures. "
                         "No diplomatic softening. Name and shame with facts.",
    "measured_criticism": "Be factual and restrained but firm. Let the data speak. "
                          "Professional tone suitable for media or educated audiences.",
    "positive_promotion": "Focus on own candidate's strengths and vision. "
                          "Inspirational tone. Avoid attacking — build a positive narrative.",
    "emotional_appeal": "Connect emotionally with voters. Use stories, metaphors, and relatable language. "
                         "Ground in real human impact. Invoke community pride and shared struggle.",
}


def get_source_data(conn, issue_ids=None, scorecard_ids=None, constituency_id=None):
    """Fetch source data for content generation."""
    c = conn.cursor()

    if not constituency_id:
        c.execute("SELECT id FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
        row = c.fetchone()
        if not row:
            return None
        constituency_id = row["id"]

    # Profile
    c.execute("SELECT * FROM constituency_profile WHERE id=?", (constituency_id,))
    profile = dict(c.fetchone())

    # Issues
    issues = []
    if issue_ids:
        placeholders = ",".join("?" * len(issue_ids))
        c.execute(f"SELECT * FROM issues WHERE id IN ({placeholders})", issue_ids)
        issues = [dict(r) for r in c.fetchall()]
    elif not scorecard_ids:
        c.execute("SELECT * FROM issues WHERE constituency_id=? ORDER BY severity DESC LIMIT 10",
                  (constituency_id,))
        issues = [dict(r) for r in c.fetchall()]

    # Scorecard
    scorecard = []
    if scorecard_ids:
        placeholders = ",".join("?" * len(scorecard_ids))
        c.execute(f"SELECT * FROM incumbent_scorecard WHERE id IN ({placeholders})", scorecard_ids)
        scorecard = [dict(r) for r in c.fetchall()]
    elif not issue_ids:
        c.execute("SELECT * FROM incumbent_scorecard WHERE constituency_id=? LIMIT 10",
                  (constituency_id,))
        scorecard = [dict(r) for r in c.fetchall()]

    # Recent sentiment
    c.execute("""
        SELECT * FROM social_sentiment WHERE constituency_id=?
        ORDER BY date DESC LIMIT 5
    """, (constituency_id,))
    sentiment = [dict(r) for r in c.fetchall()]

    return {
        "profile": profile,
        "issues": issues,
        "scorecard": scorecard,
        "sentiment": sentiment,
    }


def build_prompt(content_type, tone, source_data, custom_claim=None):
    """Build the prompt for Claude API."""
    ct = CONTENT_TYPES[content_type]
    tone_inst = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["measured_criticism"])

    profile = source_data["profile"]
    issues = source_data["issues"]
    scorecard = source_data["scorecard"]

    context_parts = []
    context_parts.append(f"Constituency: {profile['name']}, District: {profile['district']}")
    context_parts.append(f"Current MLA: {profile['current_mla']} ({profile['current_party']})")
    context_parts.append(f"2021 Margin: {profile['last_election_margin']:,} votes ({profile['last_election_margin_pct']}%)")
    context_parts.append(f"Turnout: {profile['last_election_turnout']}%")

    if issues:
        context_parts.append("\n--- ISSUES (from database) ---")
        for issue in issues:
            context_parts.append(
                f"[Issue #{issue['id']}] {issue['title']} "
                f"(Category: {issue['category']}, Severity: {issue['severity']}/5, "
                f"Status: {issue['status']})"
            )
            if issue.get('description'):
                context_parts.append(f"  Description: {issue['description']}")
            if issue.get('affected_population_estimate'):
                context_parts.append(f"  Affected: ~{issue['affected_population_estimate']:,} people")
            verified = "VERIFIED" if issue.get('verified') else "UNVERIFIED"
            context_parts.append(f"  Source: {issue.get('source', 'N/A')} [{verified}]")

    if scorecard:
        context_parts.append("\n--- INCUMBENT SCORECARD (from database) ---")
        for entry in scorecard:
            context_parts.append(
                f"[Scorecard #{entry['id']}] Promise: {entry['promise_made']} "
                f"(Status: {entry['delivery_status']})"
            )
            if entry.get('evidence'):
                context_parts.append(f"  Evidence: {entry['evidence']}")
            if entry.get('fund_allocated'):
                fund_line = f"  Funds: ₹{entry['fund_allocated']:.1f}L allocated"
                if entry.get('fund_utilized'):
                    fund_line += f", ₹{entry['fund_utilized']:.1f}L utilized"
                context_parts.append(fund_line)

    context = "\n".join(context_parts)

    prompt = f"""You are a Tamil Nadu political campaign content strategist.
Generate {ct['description']} based ONLY on the data provided below.

CRITICAL RULES:
1. NEVER fabricate statistics or claims. Every assertion must come from the data below.
2. Reference source IDs (e.g., "Issue #3", "Scorecard #1") in your citations.
3. If evidence for a claim is from an UNVERIFIED source, add [NEEDS VERIFICATION] tag.
4. Generate content in BOTH Tamil and English.
5. Tamil text must use proper Unicode Tamil script.

CONTENT TYPE: {content_type}
{ct['instruction']}

TONE: {tone}
{tone_inst}

--- SOURCE DATA ---
{context}
"""

    if custom_claim:
        prompt += f"\n--- CLAIM TO COUNTER ---\n{custom_claim}\n"

    prompt += "\nGenerate the content now. Start with Tamil version, then English version."
    prompt += "\nAt the end, list all source references used (Issue #X, Scorecard #Y)."
    prompt += "\nIf any claim uses unverified data, mark it [NEEDS VERIFICATION]."

    return prompt


def generate_with_api(prompt):
    """Call Claude API to generate content."""
    if not HAS_API:
        return None, "anthropic package not installed. Install with: pip install anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not api_key:
        return None, "ANTHROPIC_API_KEY not set. Set in environment or .env file."

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text, None


def generate_without_api(prompt, source_data, content_type, tone):
    """Generate template content without API (for testing/offline use)."""
    profile = source_data["profile"]
    issues = source_data["issues"]
    scorecard = source_data["scorecard"]

    lines = []
    lines.append(f"=== GENERATED CONTENT (TEMPLATE — API not available) ===")
    lines.append(f"Type: {content_type}")
    lines.append(f"Tone: {tone}")
    lines.append(f"Constituency: {profile['name']}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("--- Tamil Version ---")
    lines.append("[API required for Tamil content generation]")
    lines.append("")
    lines.append("--- English Version ---")

    if content_type == "social_post" and issues:
        issue = issues[0]
        lines.append(f"#{profile['name']} has been suffering from {issue['category']} issues. "
                     f"{issue['title']}. Severity: {issue['severity']}/5. "
                     f"When will MLA {profile['current_mla']} act? "
                     f"[Source: Issue #{issue['id']}]")
    elif content_type == "talking_point":
        for issue in issues:
            lines.append(f"- {issue['title']} (Severity {issue['severity']}/5) [Issue #{issue['id']}]")
        for entry in scorecard:
            lines.append(f"- Promise: {entry['promise_made'][:80]} → "
                         f"Status: {entry['delivery_status']} [Scorecard #{entry['id']}]")
    else:
        lines.append("[Full content requires Claude API. Set ANTHROPIC_API_KEY.]")
        lines.append("")
        lines.append("Available source data:")
        for issue in issues:
            lines.append(f"  Issue #{issue['id']}: {issue['title']}")
        for entry in scorecard:
            lines.append(f"  Scorecard #{entry['id']}: {entry['promise_made'][:60]}")

    lines.append("")
    lines.append("--- Source References ---")
    for issue in issues:
        verified = "VERIFIED" if issue.get("verified") else "UNVERIFIED"
        lines.append(f"Issue #{issue['id']}: {issue['title']} [{verified}]")
    for entry in scorecard:
        lines.append(f"Scorecard #{entry['id']}: {entry['promise_made'][:60]}")

    return "\n".join(lines)


def store_content(conn, content_type, tone, content_text, source_data):
    """Store generated content in content_output table."""
    c = conn.cursor()
    constituency_id = source_data["profile"]["id"]

    source_issues = json.dumps([i["id"] for i in source_data["issues"]])
    source_scorecard = json.dumps([s["id"] for s in source_data["scorecard"]])

    # Check if any source is unverified
    has_unverified = any(not i.get("verified") for i in source_data["issues"])
    fact_check = "needs_verification" if has_unverified else "pending"

    # Split Tamil/English if possible
    content_tamil = ""
    content_english = content_text
    if "Tamil Version" in content_text and "English Version" in content_text:
        parts = content_text.split("English Version")
        content_tamil = parts[0].replace("Tamil Version", "").strip().strip("-").strip()
        content_english = parts[1].strip().strip("-").strip() if len(parts) > 1 else content_text

    c.execute("""
        INSERT INTO content_output (
            constituency_id, content_type, tone,
            content_tamil, content_english,
            source_issues, source_scorecard,
            fact_check_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        constituency_id, content_type, tone,
        content_tamil, content_english,
        source_issues, source_scorecard,
        fact_check,
    ))
    conn.commit()
    return c.lastrowid


def list_sources(conn):
    """List available source data for content generation."""
    c = conn.cursor()
    c.execute("SELECT id FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
    row = c.fetchone()
    if not row:
        print(f"ERROR: {CONSTITUENCY} not found.")
        return
    cid = row["id"]

    print(f"\n=== Available Sources for {CONSTITUENCY} ===\n")

    c.execute("SELECT id, title, category, severity, verified FROM issues WHERE constituency_id=? ORDER BY severity DESC", (cid,))
    issues = c.fetchall()
    if issues:
        print("ISSUES:")
        for i in issues:
            v = "✓" if i["verified"] else "✗"
            print(f"  #{i['id']} [{v}] {i['title']} (cat: {i['category']}, sev: {i['severity']})")
    else:
        print("ISSUES: None recorded. Use field_report.py to add.")

    print()
    c.execute("SELECT id, promise_made, delivery_status FROM incumbent_scorecard WHERE constituency_id=?", (cid,))
    scorecard = c.fetchall()
    if scorecard:
        print("SCORECARD:")
        for s in scorecard:
            print(f"  #{s['id']} [{s['delivery_status']}] {s['promise_made'][:80]}")
    else:
        print("SCORECARD: None recorded. Use field_report.py or govt_data_parser.py to add.")

    print()
    c.execute("SELECT COUNT(*) as cnt FROM social_sentiment WHERE constituency_id=?", (cid,))
    print(f"SENTIMENT ENTRIES: {c.fetchone()['cnt']}")

    c.execute("SELECT COUNT(*) as cnt FROM content_output WHERE constituency_id=?", (cid,))
    print(f"GENERATED CONTENT: {c.fetchone()['cnt']}")


def main():
    parser = argparse.ArgumentParser(description="Campaign content generation engine")
    parser.add_argument("--type", choices=list(CONTENT_TYPES.keys()), default="social_post")
    parser.add_argument("--tone", choices=list(TONE_INSTRUCTIONS.keys()), default="measured_criticism")
    parser.add_argument("--issue", help="Issue ID(s), comma-separated")
    parser.add_argument("--scorecard", help="Scorecard ID(s), comma-separated")
    parser.add_argument("--claim", help="Incumbent claim to counter (for counter_narrative type)")
    parser.add_argument("--all", action="store_true", help="Use all available sources")
    parser.add_argument("--no-store", action="store_true", help="Don't store generated content")
    parser.add_argument("--list-sources", action="store_true", help="List available source data")
    parser.add_argument("--output", "-o", help="Save to file")
    args = parser.parse_args()

    conn = get_db()

    if args.list_sources:
        list_sources(conn)
        conn.close()
        return

    issue_ids = [int(x) for x in args.issue.split(",")] if args.issue else None
    scorecard_ids = [int(x) for x in args.scorecard.split(",")] if args.scorecard else None

    source_data = get_source_data(conn, issue_ids, scorecard_ids)
    if not source_data:
        print(f"ERROR: No data found for {CONSTITUENCY}. Run seed_data.py first.")
        conn.close()
        return

    if not source_data["issues"] and not source_data["scorecard"]:
        print("WARNING: No issues or scorecard data available.")
        print("Add data first with field_report.py, news_scraper.py, or govt_data_parser.py.")
        print("Run --list-sources to see what's available.")
        conn.close()
        return

    prompt = build_prompt(args.type, args.tone, source_data, args.claim)

    print(f"Generating {args.type} ({args.tone})...")
    print(f"Sources: {len(source_data['issues'])} issues, {len(source_data['scorecard'])} scorecard entries")

    content, error = generate_with_api(prompt)
    if error:
        print(f"API unavailable: {error}")
        print("Generating template content...\n")
        content = generate_without_api(prompt, source_data, args.type, args.tone)

    if not args.no_store:
        content_id = store_content(conn, args.type, args.tone, content, source_data)
        print(f"\nContent stored as #{content_id}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved to {args.output}")
    else:
        print(f"\n{'='*60}")
        print(content)
        print(f"{'='*60}")

    conn.close()


if __name__ == "__main__":
    main()
