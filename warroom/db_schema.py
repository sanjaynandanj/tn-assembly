"""
SQLite database schema for the Tamil Nadu Constituency Political Intelligence System.
Run this script to initialize or reset the database.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "warroom.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(reset=False):
    if reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS constituency_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            ac_no INTEGER,
            district TEXT NOT NULL,
            type TEXT CHECK(type IN ('urban','rural','semi-urban')),
            constituency_type TEXT,  -- GEN, SC, ST
            sub_region TEXT,
            population INTEGER,
            voter_count INTEGER,
            voter_count_2026 INTEGER,
            electors_male INTEGER,
            electors_female INTEGER,
            electors_third_gender INTEGER,
            reserved_category TEXT,
            current_mla TEXT,
            current_mla_age INTEGER,
            current_mla_sex TEXT,
            current_mla_education TEXT,
            current_mla_profession TEXT,
            current_party TEXT,
            last_election_margin INTEGER,
            last_election_margin_pct REAL,
            last_election_turnout REAL,
            last_election_valid_votes INTEGER,
            last_election_total_candidates INTEGER,
            runner_up_candidate TEXT,
            runner_up_party TEXT,
            runner_up_votes INTEGER,
            enop REAL,  -- effective number of parties
            key_demographics TEXT,  -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS candidate_2021 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            constituency_id INTEGER NOT NULL REFERENCES constituency_profile(id),
            candidate_name TEXT NOT NULL,
            party TEXT,
            position INTEGER,
            votes INTEGER,
            vote_share_pct REAL,
            age INTEGER,
            sex TEXT,
            education TEXT,
            profession TEXT,
            deposit_lost TEXT,
            incumbent TEXT,
            no_terms INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS candidate_2026 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            constituency_id INTEGER NOT NULL REFERENCES constituency_profile(id),
            candidate_name TEXT NOT NULL,
            party TEXT,
            alliance TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            constituency_id INTEGER NOT NULL REFERENCES constituency_profile(id),
            category TEXT CHECK(category IN (
                'water','roads','healthcare','education','employment',
                'corruption','caste','environment','housing','transport',
                'sanitation','agriculture','law_and_order','other'
            )),
            title TEXT NOT NULL,
            description TEXT,
            severity INTEGER CHECK(severity BETWEEN 1 AND 5),
            source TEXT,
            source_url TEXT,
            date_reported DATE,
            verified INTEGER DEFAULT 0,
            affected_population_estimate INTEGER,
            status TEXT DEFAULT 'open' CHECK(status IN ('open','partially_addressed','resolved')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS incumbent_scorecard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            constituency_id INTEGER NOT NULL REFERENCES constituency_profile(id),
            mla_name TEXT NOT NULL,
            party TEXT,
            promise_made TEXT,
            promise_category TEXT,
            promise_date DATE,
            promise_source TEXT,
            delivery_status TEXT DEFAULT 'not_started' CHECK(delivery_status IN (
                'not_started','in_progress','completed','failed'
            )),
            evidence TEXT,
            evidence_source TEXT,
            fund_allocated REAL,
            fund_utilized REAL,
            fund_source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS opposition_candidate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            constituency_id INTEGER NOT NULL REFERENCES constituency_profile(id),
            candidate_name TEXT NOT NULL,
            party TEXT,
            alliance TEXT,
            work_done TEXT,
            work_category TEXT,
            evidence TEXT,
            evidence_source TEXT,
            date DATE,
            strengths TEXT,  -- JSON
            vulnerabilities TEXT,  -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS social_sentiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            constituency_id INTEGER NOT NULL REFERENCES constituency_profile(id),
            platform TEXT CHECK(platform IN ('twitter','facebook','news','field_report','whatsapp','youtube','other')),
            content_summary TEXT,
            original_text TEXT,
            sentiment TEXT CHECK(sentiment IN ('positive','negative','neutral','mixed')),
            topic_tags TEXT,  -- JSON array
            date DATE,
            source_url TEXT,
            author TEXT,
            language TEXT DEFAULT 'tamil',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS content_output (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            constituency_id INTEGER NOT NULL REFERENCES constituency_profile(id),
            content_type TEXT CHECK(content_type IN (
                'social_post','whatsapp_forward','video_script',
                'infographic_text','talking_point','counter_narrative'
            )),
            narrative_angle TEXT,
            target_audience TEXT,
            tone TEXT CHECK(tone IN ('aggressive_attack','measured_criticism','positive_promotion','emotional_appeal')),
            content_tamil TEXT,
            content_english TEXT,
            source_issues TEXT,      -- JSON array of issue IDs
            source_scorecard TEXT,   -- JSON array of scorecard IDs
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft','reviewed','approved','published')),
            fact_check_status TEXT DEFAULT 'pending' CHECK(fact_check_status IN ('pending','verified','needs_verification','flagged')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes for common queries
    c.execute("CREATE INDEX IF NOT EXISTS idx_issues_constituency ON issues(constituency_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_issues_category ON issues(category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_issues_severity ON issues(severity DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_scorecard_constituency ON incumbent_scorecard(constituency_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_constituency ON social_sentiment(constituency_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_platform ON social_sentiment(platform)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_date ON social_sentiment(date DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_content_constituency ON content_output(constituency_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_content_status ON content_output(status)")

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    import sys
    reset = "--reset" in sys.argv
    init_db(reset=reset)
