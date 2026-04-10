# Warroom — Tamil Nadu Constituency Political Intelligence System

Single-constituency POC for **TIRUTTANI** (AC No. 3), Tiruvallur District.

Collects, structures, analyzes, and outputs campaign-ready political intelligence.

## Setup

```bash
cd warroom/
pip install -r requirements.txt
```

### Initialize Database

```bash
python seed_data.py --reset   # Create DB and seed from election data
```

This creates `warroom.db` (SQLite) populated with:
- TIRUTTANI constituency profile (2021 results)
- 14 candidates from 2021 election
- 4 declared candidates for 2026

### Environment Variables (optional)

Create a `.env` file in the `warroom/` directory:

```
ANTHROPIC_API_KEY=sk-ant-...    # For content generation
TWITTER_BEARER_TOKEN=...         # For X API search (paid tier)
```

## Architecture

```
warroom/
  db_schema.py              # SQLite schema (8 tables)
  seed_data.py              # Seed DB from existing election CSVs
  dashboard.py              # Streamlit dashboard
  requirements.txt
  warroom.db                # SQLite database (generated)

  scrapers/
    news_scraper.py         # Tamil news site scraper + CSV fallback
    twitter_search.py       # X/Twitter search + CSV template
    field_report.py         # Interactive CLI for ground reports
    govt_data_parser.py     # RTI/budget PDF parser + CSV import

  analysis/
    intelligence_report.py  # Full constituency intelligence report (Markdown)
    comparative.py          # District/state comparative analysis

  content/
    generate.py             # Claude API content generation engine

  templates/                # CSV import templates (generated)
  data/                     # Generated reports + manual import files
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `constituency_profile` | Name, district, MLA, margins, voter counts, demographics |
| `candidate_2021` | All candidates from 2021 election with votes, education, profession |
| `candidate_2026` | Declared 2026 candidates with party and alliance |
| `issues` | Ground-level issues (category, severity 1-5, status, verification) |
| `incumbent_scorecard` | MLA promises, delivery status, fund allocation/utilization |
| `opposition_candidate` | Opposition activities, work done, strengths/vulnerabilities |
| `social_sentiment` | News, tweets, field reports with sentiment + topic tags |
| `content_output` | Generated content with Tamil/English, source references, approval status |

## Usage

### 1. Data Ingestion

#### News Scraping
```bash
# Scrape all Tamil news sources
python scrapers/news_scraper.py

# Scrape single source
python scrapers/news_scraper.py --source dinamani

# Import from CSV (if scraping is blocked)
python scrapers/news_scraper.py --import templates/news_import.csv
```

#### Twitter/X
```bash
# Generate CSV template for manual data entry
python scrapers/twitter_search.py --generate-template

# Import tweets from CSV
python scrapers/twitter_search.py --import templates/twitter_import.csv

# Search via X API (needs TWITTER_BEARER_TOKEN)
python scrapers/twitter_search.py --search
```

#### Field Reports (Interactive CLI)
```bash
# Full interactive menu
python scrapers/field_report.py

# Jump to specific type
python scrapers/field_report.py --type issue
python scrapers/field_report.py --type scorecard
python scrapers/field_report.py --type opposition
python scrapers/field_report.py --type sentiment

# Bulk import from CSV
python scrapers/field_report.py --import data/issues.csv --import-type issue
python scrapers/field_report.py --import data/scorecard.csv --import-type scorecard

# Generate CSV templates
python scrapers/field_report.py --generate-templates
```

#### Government Data
```bash
# Parse a PDF (RTI response, budget doc)
python scrapers/govt_data_parser.py --pdf path/to/report.pdf

# Import from CSV template
python scrapers/govt_data_parser.py --import templates/govt_data_import.csv

# Generate template
python scrapers/govt_data_parser.py --generate-template
```

### 2. Analysis

#### Intelligence Report
```bash
# Print to terminal
python analysis/intelligence_report.py

# Save to file
python analysis/intelligence_report.py -o data/intelligence_report.md
```

Generates:
- Constituency profile with voter demographics
- 2021 results breakdown
- 2026 candidate assessment
- Top issues by severity and category
- Incumbent scorecard with performance score
- Sentiment analysis (platform, topic, trend)
- Opposition strength assessment
- Strategic vulnerabilities and strengths to counter

#### Comparative Analysis
```bash
python analysis/comparative.py
python analysis/comparative.py -o data/comparative_report.md
```

Compares TIRUTTANI against:
- All 10 Tiruvallur district constituencies
- State averages (all 234 seats)
- Competitiveness ranking

### 3. Content Generation

```bash
# List available source data
python content/generate.py --list-sources

# Generate from specific issues
python content/generate.py --type social_post --issue 1 --tone aggressive_attack
python content/generate.py --type whatsapp_forward --issue 1,2,3

# Generate from scorecard
python content/generate.py --type video_script --scorecard 1 --tone emotional_appeal

# Generate talking points from all data
python content/generate.py --type talking_point --all

# Counter a specific claim
python content/generate.py --type counter_narrative --claim "MLA built 500 new houses"

# Save to file
python content/generate.py --type social_post --issue 1 -o draft.txt
```

**Content types:** `social_post`, `whatsapp_forward`, `video_script`, `talking_point`, `counter_narrative`, `infographic_text`

**Tones:** `aggressive_attack`, `measured_criticism`, `positive_promotion`, `emotional_appeal`

All generated content:
- References source IDs (Issue #X, Scorecard #Y)
- Flags unverified claims as `[NEEDS VERIFICATION]`
- Generates in both Tamil and English
- Stored in DB with approval workflow (draft -> reviewed -> approved -> published)

### 4. Dashboard

```bash
streamlit run dashboard.py
```

Pages:
- **Overview** — Profile, top issues, scorecard status, sentiment pulse
- **Issues** — Category heatmap, severity chart, issue details with content generation
- **Scorecard** — Performance score, fund utilization, promise status
- **Sentiment** — Platform breakdown, topic analysis, recent entries
- **Content Queue** — Generated content with review/approve/publish workflow

Sidebar includes quick-generate form for on-demand content creation.

## CSV Import Formats

All scrapers have CSV fallback. Templates are in `templates/`:

| Template | Columns |
|----------|---------|
| `news_import.csv` | source, title, summary, url, date |
| `twitter_import.csv` | tweet_text, author_handle, author_name, date, tweet_url, likes, retweets, replies, language, media_type |
| `issues_import.csv` | title, description, category, severity, source, date, affected_population, status |
| `scorecard_import.csv` | promise_made, promise_category, delivery_status, evidence, fund_allocated, fund_utilized |
| `sentiment_import.csv` | platform, summary, detail, sentiment, topic, source_person, date |
| `govt_data_import.csv` | scheme, description, allocated, utilized, status, source, beneficiaries |

## Extending to All 234 Constituencies

The system is designed for multi-constituency extension:
1. `CONSTITUENCY` and `DISTRICT` constants in each script can be parameterized
2. `constituency_profile` table supports multiple entries
3. All other tables reference `constituency_id` (foreign key)
4. Seed script reads from the same CSVs used for all 234 seats
5. Analysis and content scripts accept constituency_id parameters

To scale: add a CLI flag `--constituency NAME` to each script, or build a config file.
