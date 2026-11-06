# backend/discovery/cli_importer.py
"""Command-line and programmatic runner for Phase 4A Job Discovery Source Registry.

Extracts data from the three source PDFs:
1. data/raw_sources/Daily_Job_Posting_Portals.pdf (preferred revised portals)
2. data/raw_sources/Daily_Job_Posting_Websites.pdf (older portal directory)
3. data/raw_sources/800+ IT companies master data for freshers.pdf (companies master directory)

Populates the database idempotently, generates audit logs, and prints detailed metrics.
"""

import os
import sys
import json

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from discovery.pdf_extractor import (
    extract_portals_from_pdf,
    extract_companies_from_pdf,
    generate_extraction_audit,
)
from discovery.importer import run_sync_import_pipeline, DEFAULT_DB_PATH

RAW_DATA_DIR = os.path.abspath(os.path.join(backend_dir, "..", "data", "raw_sources"))


def run_import_pipeline(dry_run: bool = False, db_path: str = DEFAULT_DB_PATH) -> dict:
    portals_revised_path = os.path.join(RAW_DATA_DIR, "Daily_Job_Posting_Portals.pdf")
    portals_older_path = os.path.join(RAW_DATA_DIR, "Daily_Job_Posting_Websites.pdf")
    companies_path = os.path.join(RAW_DATA_DIR, "800+ IT companies master data for freshers.pdf")

    print(">>> 1. Extracting Portals from Revised Directory...", flush=True)
    portals_revised = extract_portals_from_pdf(portals_revised_path)
    print(f"    Extracted {len(portals_revised)} portal entries from {os.path.basename(portals_revised_path)}", flush=True)

    print(">>> 2. Extracting Portals from Older Directory...", flush=True)
    portals_older = extract_portals_from_pdf(portals_older_path)
    print(f"    Extracted {len(portals_older)} portal entries from {os.path.basename(portals_older_path)}", flush=True)

    print(">>> 3. Extracting Companies and Email Records...", flush=True)
    companies_data, email_data = extract_companies_from_pdf(companies_path)
    print(f"    Extracted {len(companies_data)} company entries and {len(email_data)} email records", flush=True)

    # Generate extraction audit
    audit = generate_extraction_audit(portals_revised, portals_older, companies_data, email_data)
    print("\n--- EXTRACTION AUDIT REPORT ---", flush=True)
    print(json.dumps(audit, indent=2), flush=True)

    # Compare and preserve any older unique portals not present in revised
    revised_norm_urls = set(p["normalized_url"].lower() for p in portals_revised if p["normalized_url"])
    older_unique = [
        p for p in portals_older
        if p["normalized_url"] and p["normalized_url"].lower() not in revised_norm_urls
    ]
    all_portals = list(portals_revised) + older_unique
    print(f"\nTotal portals to import (revised + unique older): {len(all_portals)}", flush=True)

    print("\n>>> 4. Executing Database Import Pipeline...", flush=True)
    import_results = run_sync_import_pipeline(
        portals=all_portals,
        companies=companies_data,
        emails=email_data,
        db_path=db_path,
        dry_run=dry_run,
        portal_filename=os.path.basename(portals_revised_path),
        company_filename=os.path.basename(companies_path)
    )

    print("\n--- IMPORT EXECUTION RESULTS ---", flush=True)
    print(json.dumps(import_results, indent=2), flush=True)

    return {
        "audit": audit,
        "import_results": import_results
    }


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_import_pipeline(dry_run=dry_run)
