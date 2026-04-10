"""
Seed the warroom database with existing election data for a target constituency.
Reads from tn-2021.csv and contestants2026.json.
"""

import csv
import json
import os
import sys

from db_schema import get_db, init_db, DB_PATH

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_2021 = os.path.join(PROJECT_ROOT, "tn-2021.csv")
JSON_2026 = os.path.join(PROJECT_ROOT, "src", "data", "contestants2026.json")

TARGET_CONSTITUENCY = "TIRUTTANI"
TARGET_DISTRICT = "TIRUVALLUR"


def seed_constituency_profile(conn):
    """Seed the constituency profile from 2021 election data."""
    rows = []
    with open(CSV_2021, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Constituency_Name"].strip().upper() == TARGET_CONSTITUENCY:
                rows.append(row)

    if not rows:
        print(f"ERROR: No data found for {TARGET_CONSTITUENCY}")
        return None

    winner = next((r for r in rows if r["Position"] == "1"), None)
    runner_up = next((r for r in rows if r["Position"] == "2"), None)

    if not winner:
        print("ERROR: No winner found")
        return None

    # Load 2026 elector count if available from JSON
    voter_count_2026 = None
    json_path = os.path.join(PROJECT_ROOT, "tn-2021.json")
    try:
        with open(json_path) as f:
            jdata = json.load(f)
        fields = [fld["id"] for fld in jdata["fields"]]
        for rec in jdata["records"]:
            obj = dict(zip(fields, rec))
            if obj.get("Constituency_Name", "").upper() == TARGET_CONSTITUENCY and obj.get("Position") in (1, "1"):
                voter_count_2026 = int(obj.get("Electors_Total_2026", 0)) or None
                break
    except Exception:
        pass

    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO constituency_profile (
            name, ac_no, district, constituency_type, sub_region,
            voter_count, voter_count_2026,
            electors_male, electors_female, electors_third_gender,
            current_mla, current_mla_age, current_mla_sex,
            current_mla_education, current_mla_profession,
            current_party,
            last_election_margin, last_election_margin_pct,
            last_election_turnout, last_election_valid_votes,
            last_election_total_candidates,
            runner_up_candidate, runner_up_party, runner_up_votes,
            enop
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        TARGET_CONSTITUENCY,
        int(winner["Constituency_No"]),
        TARGET_DISTRICT,
        winner["Constituency_Type"],
        winner.get("Sub_Region", ""),
        int(winner["Electors"]) if winner["Electors"] else None,
        voter_count_2026,
        int(winner.get("Electors_Male", 0) or 0) or None,
        int(winner.get("Electors_Female", 0) or 0) or None,
        int(winner.get("Electors_ThirdGender", 0) or 0) or None,
        winner["Candidate"],
        int(winner["Age"]) if winner["Age"] else None,
        winner["Sex"],
        winner.get("MyNeta_education", ""),
        winner.get("TCPD_Prof_Main", ""),
        winner["Party"],
        int(winner["Margin"]) if winner["Margin"] else None,
        float(winner["Margin_Percentage"]) if winner["Margin_Percentage"] else None,
        float(winner["Turnout_Percentage"]) if winner["Turnout_Percentage"] else None,
        int(winner["Valid_Votes"]) if winner["Valid_Votes"] else None,
        int(winner["N_Cand"]) if winner["N_Cand"] else None,
        runner_up["Candidate"] if runner_up else None,
        runner_up["Party"] if runner_up else None,
        int(runner_up["Votes"]) if runner_up and runner_up["Votes"] else None,
        float(winner["ENOP"]) if winner["ENOP"] else None,
    ))
    conn.commit()

    constituency_id = c.lastrowid
    print(f"Seeded constituency profile: {TARGET_CONSTITUENCY} (id={constituency_id})")
    return constituency_id


def seed_2021_candidates(conn, constituency_id):
    """Seed all 2021 candidates for the constituency."""
    rows = []
    with open(CSV_2021, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Constituency_Name"].strip().upper() == TARGET_CONSTITUENCY:
                rows.append(row)

    c = conn.cursor()
    count = 0
    for row in rows:
        if row["Party"] == "NOTA":
            continue
        c.execute("""
            INSERT INTO candidate_2021 (
                constituency_id, candidate_name, party, position, votes,
                vote_share_pct, age, sex, education, profession,
                deposit_lost, incumbent, no_terms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            constituency_id,
            row["Candidate"],
            row["Party"],
            int(row["Position"]) if row["Position"] else None,
            int(row["Votes"]) if row["Votes"] else None,
            float(row["Vote_Share_Percentage"]) if row["Vote_Share_Percentage"] else None,
            int(row["Age"]) if row["Age"] else None,
            row["Sex"],
            row.get("MyNeta_education", ""),
            row.get("TCPD_Prof_Main", ""),
            row.get("Deposit_Lost", ""),
            row.get("Incumbent", ""),
            int(row.get("No_Terms", 0) or 0),
        ))
        count += 1

    conn.commit()
    print(f"Seeded {count} candidates from 2021 election")


def seed_2026_candidates(conn, constituency_id):
    """Seed 2026 declared/expected candidates."""
    with open(JSON_2026) as f:
        data = json.load(f)

    # Find Tiruttani — AC No. 3
    entry = data.get("3")
    if not entry:
        print("WARNING: No 2026 data found for AC No. 3")
        return

    c = conn.cursor()
    count = 0
    for cand in entry.get("candidates", []):
        c.execute("""
            INSERT INTO candidate_2026 (constituency_id, candidate_name, party, alliance)
            VALUES (?, ?, ?, ?)
        """, (
            constituency_id,
            cand["candidate"],
            cand["party"],
            cand["alliance"],
        ))
        count += 1

    # Also insert as opposition candidates (non-incumbent party)
    for cand in entry.get("candidates", []):
        # The incumbent is DMK — anyone else is opposition
        if cand["party"] != "DMK" and cand["party"] != "DMDK":
            c.execute("""
                INSERT INTO opposition_candidate (
                    constituency_id, candidate_name, party, alliance
                ) VALUES (?, ?, ?, ?)
            """, (
                constituency_id,
                cand["candidate"],
                cand["party"],
                cand["alliance"],
            ))

    conn.commit()
    print(f"Seeded {count} candidates for 2026 election")


def main():
    reset = "--reset" in sys.argv
    if reset or not os.path.exists(DB_PATH):
        init_db(reset=reset)

    conn = get_db()

    constituency_id = seed_constituency_profile(conn)
    if constituency_id:
        seed_2021_candidates(conn, constituency_id)
        seed_2026_candidates(conn, constituency_id)

    # Verify
    c = conn.cursor()
    c.execute("SELECT * FROM constituency_profile WHERE id=?", (constituency_id,))
    profile = c.fetchone()
    print(f"\n--- Profile ---")
    print(f"  Name: {profile['name']}")
    print(f"  District: {profile['district']}")
    print(f"  MLA: {profile['current_mla']} ({profile['current_party']})")
    print(f"  Margin: {profile['last_election_margin']} ({profile['last_election_margin_pct']}%)")
    print(f"  Turnout: {profile['last_election_turnout']}%")
    print(f"  Voters 2021: {profile['voter_count']}")
    print(f"  Voters 2026: {profile['voter_count_2026']}")

    c.execute("SELECT COUNT(*) as cnt FROM candidate_2021 WHERE constituency_id=?", (constituency_id,))
    print(f"  2021 candidates: {c.fetchone()['cnt']}")

    c.execute("SELECT COUNT(*) as cnt FROM candidate_2026 WHERE constituency_id=?", (constituency_id,))
    print(f"  2026 candidates: {c.fetchone()['cnt']}")

    c.execute("SELECT candidate_name, party, alliance FROM candidate_2026 WHERE constituency_id=?", (constituency_id,))
    print(f"\n--- 2026 Candidates ---")
    for row in c.fetchall():
        print(f"  {row['candidate_name']} ({row['party']}) - {row['alliance']}")

    conn.close()


if __name__ == "__main__":
    main()
