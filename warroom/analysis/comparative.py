"""
Comparative analysis engine.
Compares the target constituency against district and state averages.
Benchmarks incumbent performance against neighboring constituencies.

Usage:
    python comparative.py                    # Full comparative report
    python comparative.py --output comp.md   # Save to file
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_db

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_2021 = os.path.join(PROJECT_ROOT, "tn-2021.csv")

CONSTITUENCY = "TIRUTTANI"
DISTRICT = "TIRUVALLUR"


def load_all_constituencies():
    """Load all constituency-level data from tn-2021.csv (winners only)."""
    constituencies = {}
    with open(CSV_2021, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Constituency_Name"].strip()
            pos = int(row["Position"]) if row["Position"] else 99

            if pos == 1:
                constituencies[name] = {
                    "name": name,
                    "district": row["District_Name"],
                    "sub_region": row.get("Sub_Region", ""),
                    "party": row["Party"],
                    "candidate": row["Candidate"],
                    "votes": int(row["Votes"]) if row["Votes"] else 0,
                    "margin": int(row["Margin"]) if row["Margin"] else 0,
                    "margin_pct": float(row["Margin_Percentage"]) if row["Margin_Percentage"] else 0,
                    "turnout": float(row["Turnout_Percentage"]) if row["Turnout_Percentage"] else 0,
                    "electors": int(row["Electors"]) if row["Electors"] else 0,
                    "valid_votes": int(row["Valid_Votes"]) if row["Valid_Votes"] else 0,
                    "n_cand": int(row["N_Cand"]) if row["N_Cand"] else 0,
                    "enop": float(row["ENOP"]) if row["ENOP"] else 0,
                    "vote_share": float(row["Vote_Share_Percentage"]) if row["Vote_Share_Percentage"] else 0,
                    "constituency_type": row.get("Constituency_Type", "GEN"),
                }
    return constituencies


def compute_averages(constituencies, filter_fn=None):
    """Compute averages for a set of constituencies."""
    filtered = [c for c in constituencies.values() if filter_fn(c)] if filter_fn else list(constituencies.values())
    if not filtered:
        return {}

    n = len(filtered)
    return {
        "count": n,
        "avg_turnout": sum(c["turnout"] for c in filtered) / n,
        "avg_margin": sum(c["margin"] for c in filtered) / n,
        "avg_margin_pct": sum(c["margin_pct"] for c in filtered) / n,
        "avg_electors": sum(c["electors"] for c in filtered) / n,
        "avg_enop": sum(c["enop"] for c in filtered) / n,
        "avg_n_cand": sum(c["n_cand"] for c in filtered) / n,
        "avg_vote_share": sum(c["vote_share"] for c in filtered) / n,
        "party_wins": Counter(c["party"] for c in filtered),
    }


def generate_report(conn):
    all_const = load_all_constituencies()
    target = all_const.get(CONSTITUENCY)

    if not target:
        return f"ERROR: {CONSTITUENCY} not found in election data."

    state_avg = compute_averages(all_const)
    district_avg = compute_averages(all_const, lambda c: c["district"] == DISTRICT)
    district_consts = {k: v for k, v in all_const.items() if v["district"] == DISTRICT}

    lines = []
    lines.append(f"# COMPARATIVE ANALYSIS: {CONSTITUENCY}")
    lines.append(f"**District:** {DISTRICT} | **Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Comparison table
    lines.append("## 1. Key Metrics Comparison")
    lines.append("")
    lines.append("| Metric | Tiruttani | District Avg | State Avg | vs District | vs State |")
    lines.append("|--------|----------:|-------------:|----------:|:-----------:|:--------:|")

    def delta(val, avg):
        diff = val - avg
        return f"{'🟢' if diff > 0 else '🔴'} {diff:+.1f}"

    metrics = [
        ("Turnout %", target["turnout"], district_avg["avg_turnout"], state_avg["avg_turnout"]),
        ("Margin %", target["margin_pct"], district_avg["avg_margin_pct"], state_avg["avg_margin_pct"]),
        ("Margin (votes)", target["margin"], district_avg["avg_margin"], state_avg["avg_margin"]),
        ("Electors", target["electors"], district_avg["avg_electors"], state_avg["avg_electors"]),
        ("No. of Candidates", target["n_cand"], district_avg["avg_n_cand"], state_avg["avg_n_cand"]),
        ("ENOP", target["enop"], district_avg["avg_enop"], state_avg["avg_enop"]),
        ("Winner Vote Share %", target["vote_share"], district_avg["avg_vote_share"], state_avg["avg_vote_share"]),
    ]

    for label, val, dist, state in metrics:
        if isinstance(val, int):
            lines.append(f"| {label} | {val:,} | {dist:,.0f} | {state:,.0f} | {delta(val, dist)} | {delta(val, state)} |")
        else:
            lines.append(f"| {label} | {val:.1f} | {dist:.1f} | {state:.1f} | {delta(val, dist)} | {delta(val, state)} |")

    lines.append("")

    # District constituencies comparison
    lines.append("## 2. District Constituencies Comparison")
    lines.append(f"**{DISTRICT} District** — {len(district_consts)} constituencies")
    lines.append("")
    lines.append("| # | Constituency | Winner | Party | Margin % | Turnout % |")
    lines.append("|---|-------------|--------|-------|--------:|--------:|")

    sorted_district = sorted(district_consts.values(), key=lambda c: c["margin_pct"])
    for i, c in enumerate(sorted_district, 1):
        marker = " **⬅**" if c["name"] == CONSTITUENCY else ""
        lines.append(
            f"| {i} | {c['name']}{marker} | {c['candidate']} | {c['party']} | "
            f"{c['margin_pct']:.1f}% | {c['turnout']:.1f}% |"
        )

    lines.append("")

    # Competitiveness ranking
    lines.append("## 3. Competitiveness Analysis")
    lines.append("")

    # Rank by margin within district
    margin_rank = next(
        (i for i, c in enumerate(sorted_district, 1) if c["name"] == CONSTITUENCY),
        None
    )
    lines.append(f"- **District margin rank:** {margin_rank}/{len(sorted_district)} "
                 f"(1 = most competitive)")

    # Rank by margin statewide
    all_sorted = sorted(all_const.values(), key=lambda c: c["margin_pct"])
    state_rank = next(
        (i for i, c in enumerate(all_sorted, 1) if c["name"] == CONSTITUENCY),
        None
    )
    lines.append(f"- **State margin rank:** {state_rank}/{len(all_sorted)} (of 234)")

    # Classification
    margin = target["margin_pct"]
    if margin < 5:
        classification = "HIGHLY COMPETITIVE (swing seat)"
    elif margin < 10:
        classification = "COMPETITIVE (winnable with effort)"
    elif margin < 15:
        classification = "MODERATELY SAFE"
    elif margin < 20:
        classification = "SAFE"
    else:
        classification = "STRONGHOLD"

    lines.append(f"- **Classification:** {classification}")
    lines.append("")

    # Party performance in district
    lines.append("## 4. Party Performance in District")
    lines.append("")

    party_counts = district_avg["party_wins"]
    lines.append("| Party | Seats in District |")
    lines.append("|-------|------------------:|")
    for party, count in party_counts.most_common():
        lines.append(f"| {party} | {count} |")
    lines.append("")

    # Neighbors analysis
    lines.append("## 5. Neighboring Constituencies")
    lines.append("")
    lines.append("Constituencies in the same district, sorted by margin:")
    lines.append("")

    for c in sorted_district:
        if c["name"] == CONSTITUENCY:
            continue
        swing_needed = abs(target["margin_pct"] - c["margin_pct"])
        lines.append(f"- **{c['name']}** ({c['party']}) — Margin: {c['margin_pct']:.1f}%, "
                     f"Turnout: {c['turnout']:.1f}%")

    lines.append("")
    lines.append("---")
    lines.append("*Comparative analysis generated by Warroom Intelligence System*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Comparative constituency analysis")
    parser.add_argument("--output", "-o", help="Save report to file")
    args = parser.parse_args()

    conn = get_db()
    report = generate_report(conn)
    conn.close()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
