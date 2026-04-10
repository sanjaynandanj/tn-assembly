"""
Government data parser.
Parses RTI documents, budget PDFs, and government portal data.
Extracts fund allocations, scheme beneficiary counts, infrastructure project status.

Usage:
    python govt_data_parser.py --pdf report.pdf           # Parse a PDF
    python govt_data_parser.py --csv budget.csv           # Parse CSV data
    python govt_data_parser.py --import schemes.csv       # Import scheme data
    python govt_data_parser.py --generate-template        # Generate import templates
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_db

CONSTITUENCY = "TIRUTTANI"

# Keywords to identify relevant data in documents
FUND_PATTERNS = [
    r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lacs?|crores?)",
    r"([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lacs?|crores?)",
    r"allocated\s*(?:Rs\.?|INR|₹)?\s*([\d,]+)",
    r"expenditure\s*(?:Rs\.?|INR|₹)?\s*([\d,]+)",
    r"utilized\s*(?:Rs\.?|INR|₹)?\s*([\d,]+)",
]

SCHEME_KEYWORDS = [
    "MGNREGA", "PMAY", "PMGSY", "NREGA", "NRHM", "SSA",
    "Amma Unavagam", "Kudimaramathu", "MGNREGS",
    "Smart City", "AMRUT", "Swachh Bharat",
    "Jal Jeevan", "PM-KISAN", "MUDRA",
]


def get_constituency_id():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, current_mla, current_party FROM constituency_profile WHERE name=?", (CONSTITUENCY,))
    row = c.fetchone()
    conn.close()
    if not row:
        print(f"ERROR: Constituency {CONSTITUENCY} not found. Run seed_data.py first.")
        return None, None, None
    return row["id"], row["current_mla"], row["current_party"]


def parse_pdf(filepath):
    """Parse a PDF document for fund and scheme data."""
    try:
        import pdfplumber
    except ImportError:
        print("ERROR: pdfplumber not installed. Install with: pip install pdfplumber")
        print("Falling back to CSV import. Use --generate-template to get a template.")
        return []

    entries = []
    print(f"Parsing PDF: {filepath}")

    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []

            # Check if page mentions our constituency/district
            relevant = any(term.lower() in text.lower() for term in [
                "tiruttani", "tiruvallur", "திருத்தணி", "திருவள்ளூர்",
            ])

            if not relevant and not tables:
                continue

            print(f"  Page {i+1}: {'relevant' if relevant else 'has tables'}")

            # Extract fund amounts from text
            for pattern in FUND_PATTERNS:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    context_start = max(0, match.start() - 100)
                    context_end = min(len(text), match.end() + 100)
                    context = text[context_start:context_end].strip()

                    # Try to identify what scheme/project this is for
                    scheme = "Unknown"
                    for kw in SCHEME_KEYWORDS:
                        if kw.lower() in context.lower():
                            scheme = kw
                            break

                    amount_str = match.group(1).replace(",", "")
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        continue

                    # Determine if allocated or utilized based on context
                    is_utilized = any(w in context.lower() for w in ["utilized", "spent", "expenditure", "disbursed"])

                    entries.append({
                        "scheme": scheme,
                        "context": context,
                        "amount": amount,
                        "is_utilized": is_utilized,
                        "page": i + 1,
                        "source": os.path.basename(filepath),
                    })

            # Parse tables
            for table in tables:
                if not table or len(table) < 2:
                    continue
                headers = [str(h).lower().strip() if h else "" for h in table[0]]

                for row in table[1:]:
                    row_text = " ".join(str(cell) for cell in row if cell)
                    if any(term.lower() in row_text.lower() for term in ["tiruttani", "tiruvallur"]):
                        entries.append({
                            "scheme": "Table data",
                            "context": row_text,
                            "amount": None,
                            "is_utilized": False,
                            "page": i + 1,
                            "source": os.path.basename(filepath),
                        })

    print(f"  Extracted {len(entries)} potential entries")
    return entries


def parse_csv_data(filepath):
    """Parse government data from CSV format."""
    entries = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                "scheme": row.get("scheme", row.get("project", "Unknown")),
                "context": row.get("description", row.get("details", "")),
                "amount_allocated": float(row["allocated"]) if row.get("allocated") else None,
                "amount_utilized": float(row["utilized"]) if row.get("utilized") else None,
                "status": row.get("status", "not_started"),
                "source": row.get("source", os.path.basename(filepath)),
                "beneficiaries": row.get("beneficiaries", ""),
            })
    return entries


def store_entries(entries, mla_name, party, constituency_id):
    """Store parsed government data as incumbent scorecard entries."""
    conn = get_db()
    c = conn.cursor()
    stored = 0

    for entry in entries:
        promise = entry.get("scheme", "Government scheme")
        if entry.get("context"):
            promise = f"{promise}: {entry['context'][:200]}"

        fund_allocated = entry.get("amount_allocated") or (entry.get("amount") if not entry.get("is_utilized") else None)
        fund_utilized = entry.get("amount_utilized") or (entry.get("amount") if entry.get("is_utilized") else None)

        status = entry.get("status", "not_started")
        if fund_utilized and fund_allocated:
            ratio = fund_utilized / fund_allocated
            if ratio >= 0.9:
                status = "completed"
            elif ratio > 0:
                status = "in_progress"

        c.execute("""
            INSERT INTO incumbent_scorecard (
                constituency_id, mla_name, party, promise_made, promise_category,
                delivery_status, evidence, evidence_source,
                fund_allocated, fund_utilized, fund_source
            ) VALUES (?, ?, ?, ?, 'other', ?, ?, ?, ?, ?, ?)
        """, (
            constituency_id, mla_name, party, promise,
            status,
            entry.get("beneficiaries", ""),
            entry.get("source", "government_data"),
            fund_allocated,
            fund_utilized,
            entry.get("source", ""),
        ))
        stored += 1

    conn.commit()
    conn.close()
    print(f"Stored {stored} entries in incumbent_scorecard")


def generate_template():
    """Generate CSV template for government data import."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    os.makedirs(template_dir, exist_ok=True)
    path = os.path.join(template_dir, "govt_data_import.csv")

    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scheme", "description", "allocated", "utilized", "status", "source", "beneficiaries"])
        w.writerow([
            "PMAY-G", "Pradhan Mantri Awas Yojana - Rural housing",
            "500", "320", "in_progress", "RTI response 2026",
            "1200 houses sanctioned, 780 completed"
        ])
        w.writerow([
            "MGNREGS", "MGNREGA employment days",
            "200", "180", "in_progress", "nrega.nic.in",
            "45000 person-days generated"
        ])
        w.writerow([
            "Kudimaramathu", "Water body restoration",
            "75", "10", "not_started", "district collector report",
            "3 lakes identified, work not started"
        ])

    print(f"Template created: {path}")
    print("\nColumns:")
    print("  scheme: Name of the scheme/project")
    print("  description: What it is")
    print("  allocated: Fund allocated in lakhs")
    print("  utilized: Fund utilized in lakhs")
    print("  status: not_started / in_progress / completed / failed")
    print("  source: Where you got this data (RTI, website, etc.)")
    print("  beneficiaries: Beneficiary count or description")


def main():
    parser = argparse.ArgumentParser(description="Government data parser for constituency intelligence")
    parser.add_argument("--pdf", help="Parse a PDF document")
    parser.add_argument("--csv", help="Parse government data from CSV")
    parser.add_argument("--import", dest="import_file", help="Import scheme data from CSV template")
    parser.add_argument("--generate-template", action="store_true", help="Generate CSV import template")
    args = parser.parse_args()

    if args.generate_template:
        generate_template()
        return

    constituency_id, mla_name, party = get_constituency_id()
    if not constituency_id:
        return

    if args.pdf:
        entries = parse_pdf(args.pdf)
        if entries:
            store_entries(entries, mla_name, party, constituency_id)
    elif args.csv or args.import_file:
        filepath = args.csv or args.import_file
        entries = parse_csv_data(filepath)
        if entries:
            store_entries(entries, mla_name, party, constituency_id)
    else:
        print("Government Data Parser")
        print("=" * 40)
        print(f"Constituency: {CONSTITUENCY}")
        print(f"MLA: {mla_name} ({party})")
        print()
        print("Usage:")
        print("  --pdf FILEPATH         Parse a PDF document")
        print("  --csv FILEPATH         Parse data from CSV")
        print("  --import FILEPATH      Import from template CSV")
        print("  --generate-template    Generate a CSV template")


if __name__ == "__main__":
    main()
