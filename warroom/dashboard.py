"""
Warroom Dashboard — Streamlit-based constituency intelligence dashboard.

Usage:
    streamlit run dashboard.py
"""

import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime

try:
    import streamlit as st
    import pandas as pd
except ImportError:
    print("ERROR: streamlit and pandas required.")
    print("Install with: pip install streamlit pandas")
    sys.exit(1)

from db_schema import get_db

CONSTITUENCY = "TIRUTTANI"

st.set_page_config(
    page_title=f"Warroom — {CONSTITUENCY}",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_data():
    """Fetch all data from database."""
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
    row = c.fetchone()
    profile = dict(row) if row else {}

    if not profile:
        conn.close()
        return None

    cid = profile["id"]

    c.execute("SELECT * FROM candidate_2021 WHERE constituency_id=? ORDER BY position", (cid,))
    candidates_2021 = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM candidate_2026 WHERE constituency_id=?", (cid,))
    candidates_2026 = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM issues WHERE constituency_id=? ORDER BY severity DESC", (cid,))
    issues = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM incumbent_scorecard WHERE constituency_id=?", (cid,))
    scorecard = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM opposition_candidate WHERE constituency_id=?", (cid,))
    opposition = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM social_sentiment WHERE constituency_id=? ORDER BY date DESC", (cid,))
    sentiment = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM content_output WHERE constituency_id=? ORDER BY created_at DESC", (cid,))
    content = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        "profile": profile,
        "candidates_2021": candidates_2021,
        "candidates_2026": candidates_2026,
        "issues": issues,
        "scorecard": scorecard,
        "opposition": opposition,
        "sentiment": sentiment,
        "content": content,
    }


def render_profile(data):
    """Render constituency profile section."""
    p = data["profile"]

    st.header(f"🎯 {p['name']} — {p['district']}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current MLA", f"{p['current_mla']}", f"{p['current_party']}")
    with col2:
        st.metric("2021 Margin", f"{p['last_election_margin']:,}", f"{p['last_election_margin_pct']}%")
    with col3:
        st.metric("Turnout", f"{p['last_election_turnout']}%")
    with col4:
        voter_change = ""
        if p.get("voter_count_2026") and p.get("voter_count"):
            change = p["voter_count_2026"] - p["voter_count"]
            voter_change = f"{change:+,}"
        st.metric("Voters (2026)", f"{p.get('voter_count_2026', 'N/A'):,}" if p.get('voter_count_2026') else "N/A",
                  voter_change)

    # 2021 Results
    with st.expander("📊 2021 Election Results", expanded=False):
        if data["candidates_2021"]:
            df = pd.DataFrame(data["candidates_2021"])
            df = df[["position", "candidate_name", "party", "votes", "vote_share_pct", "deposit_lost"]]
            df.columns = ["Pos", "Candidate", "Party", "Votes", "Vote Share %", "Deposit Lost"]
            st.dataframe(df, use_container_width=True, hide_index=True)

    # 2026 Candidates
    if data["candidates_2026"]:
        with st.expander("🗳️ 2026 Declared Candidates", expanded=False):
            df = pd.DataFrame(data["candidates_2026"])
            df = df[["candidate_name", "party", "alliance"]]
            df.columns = ["Candidate", "Party", "Alliance"]
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_issues(data):
    """Render issues heatmap and list."""
    st.header("🔥 Issues")

    issues = data["issues"]
    if not issues:
        st.info("No issues recorded yet. Use `field_report.py` to add ground-level issues.")
        return

    # Category heatmap
    cat_data = {}
    for issue in issues:
        cat = issue["category"]
        if cat not in cat_data:
            cat_data[cat] = {"count": 0, "total_severity": 0, "open": 0}
        cat_data[cat]["count"] += 1
        cat_data[cat]["total_severity"] += issue["severity"]
        if issue["status"] == "open":
            cat_data[cat]["open"] += 1

    df_cat = pd.DataFrame([
        {
            "Category": cat,
            "Count": d["count"],
            "Avg Severity": round(d["total_severity"] / d["count"], 1),
            "Open": d["open"],
        }
        for cat, d in cat_data.items()
    ]).sort_values("Avg Severity", ascending=False)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Category Breakdown")
        st.dataframe(df_cat, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Issue Severity Distribution")
        st.bar_chart(df_cat.set_index("Category")["Avg Severity"])

    # Issues list
    st.subheader("All Issues")
    for issue in issues:
        severity_color = "🔴" if issue["severity"] >= 4 else "🟡" if issue["severity"] >= 3 else "🟢"
        verified = "✅" if issue["verified"] else "❓"

        with st.expander(f"{severity_color} [{issue['severity']}/5] {issue['title']} ({issue['category']}) {verified}"):
            st.write(f"**Description:** {issue.get('description', 'N/A')}")
            st.write(f"**Status:** {issue['status']} | **Source:** {issue.get('source', 'N/A')} | "
                     f"**Reported:** {issue.get('date_reported', 'N/A')}")
            if issue.get("affected_population_estimate"):
                st.write(f"**Affected population:** ~{issue['affected_population_estimate']:,}")

            # Quick content generation button
            if st.button(f"Generate content for Issue #{issue['id']}", key=f"gen_issue_{issue['id']}"):
                st.session_state[f"generate_issue_{issue['id']}"] = True
                st.info(f"Run: `python content/generate.py --type social_post --issue {issue['id']}`")


def render_scorecard(data):
    """Render incumbent scorecard."""
    st.header(f"📋 Incumbent Scorecard — {data['profile']['current_mla']}")

    scorecard = data["scorecard"]
    if not scorecard:
        st.info("No scorecard entries yet. Use `field_report.py` or `govt_data_parser.py` to add data.")
        return

    # Summary metrics
    total = len(scorecard)
    status_counts = Counter(e["delivery_status"] for e in scorecard)
    completed = status_counts.get("completed", 0)
    failed = status_counts.get("failed", 0)
    in_progress = status_counts.get("in_progress", 0)
    not_started = status_counts.get("not_started", 0)

    score = ((completed * 1.0 + in_progress * 0.5) / total) * 100 if total > 0 else 0
    total_allocated = sum(e["fund_allocated"] or 0 for e in scorecard)
    total_utilized = sum(e["fund_utilized"] or 0 for e in scorecard)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Score", f"{score:.0f}/100")
    with col2:
        st.metric("Completed", f"{completed}/{total}")
    with col3:
        st.metric("Failed", f"{failed}/{total}")
    with col4:
        st.metric("Funds Allocated", f"₹{total_allocated:.0f}L" if total_allocated else "N/A")
    with col5:
        util_pct = (total_utilized / total_allocated * 100) if total_allocated > 0 else 0
        st.metric("Utilization", f"{util_pct:.0f}%" if total_allocated else "N/A")

    # Status breakdown
    status_df = pd.DataFrame([
        {"Status": s.replace("_", " ").title(), "Count": c}
        for s, c in status_counts.items()
    ])
    st.bar_chart(status_df.set_index("Status"))

    # Entries
    status_emoji = {"completed": "✅", "in_progress": "🔄", "not_started": "⏳", "failed": "❌"}
    for entry in scorecard:
        emoji = status_emoji.get(entry["delivery_status"], "❓")
        with st.expander(f"{emoji} {entry['promise_made'][:80]}"):
            st.write(f"**Status:** {entry['delivery_status']}")
            if entry.get("evidence"):
                st.write(f"**Evidence:** {entry['evidence']}")
            if entry.get("fund_allocated"):
                fund_text = f"**Funds:** ₹{entry['fund_allocated']:.1f}L allocated"
                if entry.get("fund_utilized"):
                    fund_text += f", ₹{entry['fund_utilized']:.1f}L utilized"
                st.write(fund_text)

            if st.button(f"Generate content for Scorecard #{entry['id']}", key=f"gen_sc_{entry['id']}"):
                st.info(f"Run: `python content/generate.py --type talking_point --scorecard {entry['id']}`")


def render_sentiment(data):
    """Render sentiment analysis section."""
    st.header("💬 Sentiment")

    entries = data["sentiment"]
    if not entries:
        st.info("No sentiment data yet. Use scrapers or `field_report.py` to add entries.")
        return

    # Overall breakdown
    sentiment_counts = Counter(e["sentiment"] for e in entries)
    total = len(entries)

    col1, col2, col3, col4 = st.columns(4)
    colors = {"positive": "🟢", "negative": "🔴", "neutral": "⚪", "mixed": "🟡"}
    for col, (sent, emoji) in zip([col1, col2, col3, col4], colors.items()):
        count = sentiment_counts.get(sent, 0)
        pct = count / total * 100 if total > 0 else 0
        with col:
            st.metric(f"{emoji} {sent.title()}", f"{count}", f"{pct:.0f}%")

    # Platform breakdown
    platform_counts = Counter(e["platform"] for e in entries)
    platform_df = pd.DataFrame([
        {"Platform": p, "Count": c} for p, c in platform_counts.most_common()
    ])
    st.bar_chart(platform_df.set_index("Platform"))

    # Recent entries
    st.subheader("Recent Entries")
    for entry in entries[:20]:
        emoji = colors.get(entry["sentiment"], "⚪")
        st.write(f"{emoji} **[{entry['platform']}]** {entry['content_summary'][:150]}")
        st.caption(f"Date: {entry.get('date', 'N/A')} | Author: {entry.get('author', 'N/A')}")


def render_content(data):
    """Render content generation queue."""
    st.header("📝 Generated Content")

    content = data["content"]
    if not content:
        st.info("No content generated yet. Use `content/generate.py` to create campaign content.")
        return

    # Status summary
    status_counts = Counter(c["status"] for c in content)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Draft", status_counts.get("draft", 0))
    with col2:
        st.metric("Reviewed", status_counts.get("reviewed", 0))
    with col3:
        st.metric("Approved", status_counts.get("approved", 0))
    with col4:
        st.metric("Published", status_counts.get("published", 0))

    # Content list
    for item in content:
        fact_emoji = {"verified": "✅", "pending": "⏳", "needs_verification": "⚠️", "flagged": "🚩"}
        fc = fact_emoji.get(item.get("fact_check_status", "pending"), "❓")

        with st.expander(
            f"[{item['content_type']}] {item.get('tone', '')} — {fc} {item['status']}"
        ):
            if item.get("content_english"):
                st.subheader("English")
                st.write(item["content_english"][:500])
            if item.get("content_tamil"):
                st.subheader("Tamil")
                st.write(item["content_tamil"][:500])

            st.caption(f"Sources — Issues: {item.get('source_issues', '[]')} | "
                      f"Scorecard: {item.get('source_scorecard', '[]')}")

            # Approval buttons
            col1, col2, col3 = st.columns(3)
            conn = get_db()
            with col1:
                if item["status"] == "draft" and st.button("Mark Reviewed", key=f"rev_{item['id']}"):
                    conn.execute("UPDATE content_output SET status='reviewed' WHERE id=?", (item["id"],))
                    conn.commit()
                    st.rerun()
            with col2:
                if item["status"] in ("draft", "reviewed") and st.button("Approve", key=f"app_{item['id']}"):
                    conn.execute("UPDATE content_output SET status='approved' WHERE id=?", (item["id"],))
                    conn.commit()
                    st.rerun()
            with col3:
                if st.button("Mark Published", key=f"pub_{item['id']}"):
                    conn.execute("UPDATE content_output SET status='published' WHERE id=?", (item["id"],))
                    conn.commit()
                    st.rerun()
            conn.close()


def render_quick_generate():
    """Quick content generation form in sidebar."""
    st.sidebar.header("⚡ Quick Generate")

    content_type = st.sidebar.selectbox("Content Type", [
        "social_post", "whatsapp_forward", "video_script",
        "talking_point", "counter_narrative", "infographic_text",
    ])
    tone = st.sidebar.selectbox("Tone", [
        "measured_criticism", "aggressive_attack",
        "positive_promotion", "emotional_appeal",
    ])
    issue_ids = st.sidebar.text_input("Issue IDs (comma-separated)", placeholder="1,2,3")
    scorecard_ids = st.sidebar.text_input("Scorecard IDs (comma-separated)", placeholder="1,2")

    if st.sidebar.button("🚀 Generate Content"):
        cmd = f"python content/generate.py --type {content_type} --tone {tone}"
        if issue_ids:
            cmd += f" --issue {issue_ids}"
        if scorecard_ids:
            cmd += f" --scorecard {scorecard_ids}"
        st.sidebar.code(cmd)
        st.sidebar.info("Run this command in the warroom/ directory")


def main():
    data = get_data()
    if not data:
        st.error(f"Constituency {CONSTITUENCY} not found in database. Run `python seed_data.py` first.")
        return

    # Sidebar navigation
    st.sidebar.title("🎯 Warroom")
    st.sidebar.caption(f"{CONSTITUENCY}, {data['profile']['district']}")

    page = st.sidebar.radio("Navigate", [
        "Overview",
        "Issues",
        "Scorecard",
        "Sentiment",
        "Content Queue",
    ])

    render_quick_generate()

    # Database stats in sidebar
    st.sidebar.markdown("---")
    st.sidebar.caption("Database Stats")
    st.sidebar.text(f"Issues: {len(data['issues'])}")
    st.sidebar.text(f"Scorecard: {len(data['scorecard'])}")
    st.sidebar.text(f"Sentiment: {len(data['sentiment'])}")
    st.sidebar.text(f"Content: {len(data['content'])}")
    st.sidebar.text(f"Opposition: {len(data['opposition'])}")

    if page == "Overview":
        render_profile(data)
        st.markdown("---")
        # Quick stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Top Issues")
            for issue in data["issues"][:5]:
                sev = "🔴" if issue["severity"] >= 4 else "🟡" if issue["severity"] >= 3 else "🟢"
                st.write(f"{sev} {issue['title']}")
            if not data["issues"]:
                st.caption("No issues yet")
        with col2:
            st.subheader("Scorecard Status")
            if data["scorecard"]:
                status_counts = Counter(e["delivery_status"] for e in data["scorecard"])
                for status, count in status_counts.items():
                    st.write(f"{status.replace('_', ' ').title()}: {count}")
            else:
                st.caption("No entries yet")
        with col3:
            st.subheader("Sentiment Pulse")
            if data["sentiment"]:
                sent_counts = Counter(e["sentiment"] for e in data["sentiment"])
                for sent, count in sent_counts.items():
                    emoji = {"positive": "🟢", "negative": "🔴", "neutral": "⚪", "mixed": "🟡"}.get(sent, "⚪")
                    st.write(f"{emoji} {sent.title()}: {count}")
            else:
                st.caption("No sentiment data yet")

    elif page == "Issues":
        render_issues(data)
    elif page == "Scorecard":
        render_scorecard(data)
    elif page == "Sentiment":
        render_sentiment(data)
    elif page == "Content Queue":
        render_content(data)


if __name__ == "__main__":
    main()
