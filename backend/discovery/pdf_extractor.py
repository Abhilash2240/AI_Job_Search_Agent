# backend/discovery/pdf_extractor.py
"""Controlled PDF extraction pipeline for portals and companies.

Strictly follows Phase 4A requirements:
- Controlled extraction using PyMuPDF (fitz).
- Preserves original source values alongside normalized representations.
- Distinguishes missing values from extraction failures.
- Extracts portals (name, URL, category, scope, document, page).
- Extracts companies (name, career URL, LinkedIn URL, contact emails, document, page).
- Handles multi-line names, wrapped URLs, and multi-email contact records.
- Generates extraction audit reports prior to database persistence.
"""

import os
import re
import fitz
from typing import List, Dict, Tuple, Optional, Any
from urllib.parse import urlparse

from discovery.url_validator import normalize_url, is_placeholder
from discovery.company_normalizer import normalize_company_name, classify_company_relevance


def extract_portals_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract structured job portal records from a portal directory PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    filename = os.path.basename(pdf_path)
    doc = fitz.open(pdf_path)
    extracted_portals: List[Dict[str, Any]] = []
    
    current_category = "General / All-Degree"

    for pno in range(len(doc)):
        page = doc[pno]
        page_num = pno + 1
        blocks = page.get_text("blocks")

        for b in blocks:
            text = b[4].strip()
            if not text:
                continue

            # Skip header, title banners, and footer lines
            if any(h in text for h in [
                "India Job Portals Directory",
                "INDIA JOB PORTALS",
                "Private-sector job discovery",
                "Quick Navigation Directory",
                "Only site name + clickable",
            ]):
                continue

            if text == "SITE" or text == "JOBS / CAREERS LINK" or text.startswith("SITE\nJOBS / CAREERS LINK"):
                continue

            lines = [l.strip() for l in text.splitlines() if l.strip()]

            # Category section header detection
            if len(lines) == 1:
                first_line = lines[0]
                if not any(first_line.startswith(p) for p in ["http://", "https://", "www."]) and not any(
                    ext in first_line for ext in [".com", ".in", ".org", ".io", ".net", ".app", ".co", ".ai"]
                ):
                    current_category = first_line.replace("\ufffd", " - ").strip()
                    continue

            # Portal site name and URL detection
            # Find the first line that looks like a URL
            http_idx = None
            for idx, l in enumerate(lines):
                if l.startswith("http://") or l.startswith("https://") or l.startswith("www."):
                    http_idx = idx
                    break

            if http_idx is not None and http_idx > 0:
                site_name = " ".join(lines[:http_idx]).replace("\ufffd", " - ").strip()
                # Reassemble potentially wrapped URL lines
                raw_url = "".join(lines[http_idx:]).replace(" ", "")

                norm_url, ver_status, domain = normalize_url(raw_url)

                # Geographic scope detection
                scope = "Global" if any(w in site_name.lower() or w in (raw_url or "").lower() for w in ["remote", "global", "nomad", "arc", "turing"]) else "India"

                extracted_portals.append({
                    "name": site_name,
                    "base_url": raw_url,
                    "normalized_url": norm_url or raw_url,
                    "category": current_category,
                    "country_scope": scope,
                    "source_document": filename,
                    "source_page": page_num,
                    "verification_status": ver_status,
                    "primary_domain": domain,
                })

    doc.close()
    return extracted_portals


def extract_companies_from_pdf(pdf_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract master company directory (Section 1) and email contact records (Section 2).
    
    Returns:
    --------
    (companies_list, email_contacts_list)
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    filename = os.path.basename(pdf_path)
    doc = fitz.open(pdf_path)

    # Collect all lines with page numbers up to Section 3 (application templates)
    all_lines: List[Tuple[int, str]] = []
    for pno in range(min(30, len(doc))):
        for line in doc[pno].get_text().splitlines():
            clean = line.strip()
            if clean:
                all_lines.append((pno + 1, clean))

    doc.close()

    # Identify boundary between Section 1 and Section 2
    split_idx = next(
        (i for i, (p, l) in enumerate(all_lines) if "2. ALL AVAILABLE EMAIL CONTACTS" in l),
        len(all_lines)
    )
    
    # Identify boundary where Section 2 ends
    end_s2_idx = next(
        (i for i, (p, l) in enumerate(all_lines) if "3. FRESHER JOB APPLICATION" in l),
        len(all_lines)
    )

    sec1_lines = all_lines[:split_idx]
    sec2_lines = all_lines[split_idx:end_s2_idx]

    # --- 1. Parse Section 1 (Master Company Directory: S.No. 1 to 846) ---
    sno_indices = [
        i for i, (p, l) in enumerate(sec1_lines)
        if l.isdigit() and 1 <= int(l) <= 846
    ]
    sno_indices.append(len(sec1_lines))

    companies: List[Dict[str, Any]] = []

    for k in range(len(sno_indices) - 1):
        start = sno_indices[k]
        end = sno_indices[k + 1]
        raw_slice = sec1_lines[start:end]
        page_num = raw_slice[0][0]

        items = [
            l for p, l in raw_slice
            if l and not any(h in l for h in [
                "Master Company Career",
                "Page ",
                "MASTER COMPANY CAREER",
                "846 unique",
                "1. MASTER COMPANY",
                "S.No.",
                "Company Name",
                "Career Site Link",
                "LinkedIn Link",
                "HR / Contact Email"
            ])
        ]

        if not items:
            continue

        sno = int(items[0])
        tokens = items[1:]

        # Special known multi-line company name handling
        if sno == 496 and len(tokens) >= 4:
            # Mercedes-Benz Research & Development India
            cname = f"{tokens[0]} {tokens[1]}"
            career = tokens[2]
            linkedin = tokens[3]
            email_tokens = tokens[4:]
        elif sno == 712 and len(tokens) >= 4:
            # SuperGaming (Supergame Appeartome Pvt Ltd)
            cname = f"{tokens[0]} {tokens[1]}"
            career = tokens[2]
            linkedin = tokens[3]
            email_tokens = tokens[4:]
        else:
            cname = tokens[0] if tokens else f"Company #{sno}"
            career = tokens[1] if len(tokens) > 1 else None
            linkedin = tokens[2] if len(tokens) > 2 else None
            email_tokens = tokens[3:] if len(tokens) > 3 else []

        # Extract genuine email addresses from email tokens
        emails = [t for t in email_tokens if "@" in t]

        # Clean placeholders
        career_raw = None if is_placeholder(career) else career
        linkedin_raw = None if is_placeholder(linkedin) else linkedin

        # Normalize career URL
        norm_career, career_status, career_domain = normalize_url(career_raw)
        norm_linkedin, linkedin_status, _ = normalize_url(linkedin_raw)

        norm_name = normalize_company_name(cname)
        relevance_cat, industry = classify_company_relevance(cname, norm_career, norm_linkedin)

        companies.append({
            "sno": sno,
            "canonical_name": cname,
            "normalized_name": norm_name,
            "career_url": career_raw,
            "normalized_career_url": norm_career,
            "career_status": career_status,
            "primary_domain": career_domain,
            "linkedin_url": linkedin_raw,
            "normalized_linkedin_url": norm_linkedin,
            "linkedin_status": linkedin_status,
            "contact_emails": emails,
            "relevance_category": relevance_cat,
            "industry": industry,
            "source_document": filename,
            "source_page": page_num,
        })

    # --- 2. Parse Section 2 (All Available Email Contacts: S.No. 1 to 95) ---
    sno2_indices = [
        i for i, (p, l) in enumerate(sec2_lines)
        if l.isdigit() and 1 <= int(l) <= 95
    ]
    sno2_indices.append(len(sec2_lines))

    email_contacts: List[Dict[str, Any]] = []

    for k in range(len(sno2_indices) - 1):
        s = sno2_indices[k]
        e = sno2_indices[k + 1]
        raw_slice = sec2_lines[s:e]
        page_num = raw_slice[0][0]

        items = [
            l for p, l in raw_slice
            if l and not any(h in l for h in [
                "Master Company",
                "Page ",
                "2. ALL AVAILABLE",
                "Separate outreach",
                "S.No.",
                "Company Name",
                "Email"
            ])
        ]

        if len(items) >= 3 and "@" in items[2]:
            email_contacts.append({
                "sno": int(items[0]),
                "company_name": items[1],
                "normalized_name": normalize_company_name(items[1]),
                "email": items[2].strip().lower(),
                "source_document": filename,
                "source_page": page_num,
            })

    return companies, email_contacts


def generate_extraction_audit(
    portals_revised: List[Dict[str, Any]],
    portals_older: List[Dict[str, Any]],
    companies_data: List[Dict[str, Any]],
    email_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate a comprehensive extraction audit report comparing datasets before DB persistence."""
    # Portal audit
    revised_urls = [p["normalized_url"] for p in portals_revised if p["normalized_url"]]
    unique_portal_urls = set(revised_urls)
    
    # Identify unique portals in older PDF not in revised
    older_unique = [
        p for p in portals_older
        if p["normalized_url"] and p["normalized_url"] not in unique_portal_urls
    ]

    # Company audit
    all_c_names = [c["canonical_name"] for c in companies_data]
    unique_norm_names = set(c["normalized_name"] for c in companies_data)
    
    career_urls = [c["normalized_career_url"] for c in companies_data if c["normalized_career_url"]]
    unique_career_urls = set(career_urls)

    # Emails
    sec1_emails = [e for c in companies_data for e in c["contact_emails"]]
    unique_sec1_emails = set(e.lower() for e in sec1_emails)
    
    sec2_emails = [e["email"] for e in email_data]
    unique_sec2_emails = set(sec2_emails)
    
    all_emails = unique_sec1_emails.union(unique_sec2_emails)

    # Needs review count (truncated or suspicious URLs)
    needs_review_career = sum(
        1 for c in companies_data
        if c.get("career_status") == "REQUIRES_MANUAL_REVIEW"
    )
    needs_review_linkedin = sum(
        1 for c in companies_data
        if c.get("linkedin_status") == "REQUIRES_MANUAL_REVIEW"
    )

    duplicate_company_occurrences = len(companies_data) - len(unique_norm_names)

    return {
        "portals": {
            "revised_extracted": len(portals_revised),
            "older_extracted": len(portals_older),
            "unique_normalized_portal_urls": len(unique_portal_urls),
            "older_unique_portals_preserved": len(older_unique),
            "total_portal_records": len(portals_revised) + len(older_unique),
        },
        "companies": {
            "total_extracted": len(companies_data),
            "unique_canonical_names": len(set(all_c_names)),
            "unique_normalized_companies": len(unique_norm_names),
            "duplicate_company_occurrences": duplicate_company_occurrences,
            "total_career_urls_extracted": len(career_urls),
            "unique_career_urls": len(unique_career_urls),
            "total_linkedin_urls_extracted": sum(1 for c in companies_data if c["linkedin_url"]),
            "career_urls_requiring_review": needs_review_career,
            "linkedin_urls_requiring_review": needs_review_linkedin,
        },
        "contacts": {
            "section1_emails_count": len(sec1_emails),
            "section2_email_records": len(email_data),
            "unique_verified_emails": len(all_emails),
        }
    }

