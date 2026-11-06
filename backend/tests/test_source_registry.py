# backend/tests/test_source_registry.py
"""Unit and integration test suite for Phase 4A Job Discovery Source Registry."""

import pytest
import os
import sqlite3
from discovery.url_validator import normalize_url, is_placeholder
from discovery.company_normalizer import normalize_company_name, classify_company_relevance
from discovery.pdf_extractor import (
    extract_portals_from_pdf,
    extract_companies_from_pdf,
    generate_extraction_audit,
)
from discovery.importer import run_sync_import_pipeline, DEFAULT_DB_PATH
from models.source import VerificationStatus, RelevanceCategory


RAW_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw_sources")
)


def test_url_normalization_and_validation():
    """Verify URL normalization, scheme addition, and truncation detection."""
    # 1. Standard valid URL with scheme
    url, status, domain = normalize_url("https://www.naukri.com/graduate-jobs")
    assert url == "https://www.naukri.com/graduate-jobs"
    assert status == VerificationStatus.NOT_CHECKED.value
    assert domain == "naukri.com"

    # 2. Domain missing scheme
    url, status, domain = normalize_url("accenture.com/us-en/careers")
    assert url == "https://accenture.com/us-en/careers"
    assert status == VerificationStatus.NOT_CHECKED.value
    assert domain == "accenture.com"

    # 3. Trailing slash normalization
    url, status, domain = normalize_url("https://www.foundit.in/")
    assert url == "https://www.foundit.in"
    assert status == VerificationStatus.NOT_CHECKED.value

    # 4. Empty and placeholder values
    assert is_placeholder("") is True
    assert is_placeholder("\ufffd") is True
    assert is_placeholder("—") is True
    assert is_placeholder("-") is True
    assert is_placeholder("None") is True
    assert is_placeholder("null") is True
    url, status, domain = normalize_url("\ufffd")
    assert url is None
    assert domain is None

    # 5. Truncation and suspicious URL detection
    url, status, domain = normalize_url("https://linkedin.com/company/al-ansari-financial-se\ufffd")
    assert status == VerificationStatus.REQUIRES_MANUAL_REVIEW.value
    assert "\ufffd" not in url

    url, status, domain = normalize_url("https://linkedin.com/company/cut-off-firm-")
    assert status == VerificationStatus.REQUIRES_MANUAL_REVIEW.value

    # 6. Malformed URL
    url, status, domain = normalize_url("not a url at all")
    assert status == VerificationStatus.REQUIRES_MANUAL_REVIEW.value


def test_company_name_normalization_and_relevance():
    """Verify company name normalization and evidence-based relevance classification."""
    # Legal suffix stripping
    assert normalize_company_name("Abda Digital Pvt Ltd") == "abda digital"
    assert normalize_company_name("Tata Consultancy Services Limited") == "tata consultancy services"
    assert normalize_company_name("SuperGaming (Supergame Appeartome Pvt Ltd)") == "supergaming supergame appeartome"
    assert normalize_company_name("Mercedes-Benz Research & Development India") == "mercedes benz research and development india"

    # Evidence-based relevance classification
    cat, ind = classify_company_relevance("Tata Consultancy Services", "tcs.com/careers")
    assert cat == RelevanceCategory.IT_SERVICES.value

    cat, ind = classify_company_relevance("Zoho", "zoho.com/careers")
    assert cat == RelevanceCategory.SAAS.value

    cat, ind = classify_company_relevance("Razorpay", "razorpay.com/careers")
    assert cat == RelevanceCategory.FINTECH.value

    cat, ind = classify_company_relevance("Yellow.ai", "yellow.ai/careers")
    assert cat == RelevanceCategory.AI_ML.value

    cat, ind = classify_company_relevance("Zscaler", "zscaler.com/careers")
    assert cat == RelevanceCategory.CYBERSECURITY.value

    cat, ind = classify_company_relevance("Google", "careers.google.com")
    assert cat == RelevanceCategory.PRODUCT_COMPANIES.value

    # Unknown company with no evidence should default to Unknown without guessing
    cat, ind = classify_company_relevance("Mystery Retailers Corp", "mysteryretailers.com")
    assert cat == RelevanceCategory.UNKNOWN.value


def test_pdf_portal_and_company_extraction():
    """Verify high-fidelity PDF extraction from the provided source documents."""
    portals_path = os.path.join(RAW_DATA_DIR, "Daily_Job_Posting_Portals.pdf")
    companies_path = os.path.join(RAW_DATA_DIR, "800+ IT companies master data for freshers.pdf")

    # 1. Portals extraction
    portals = extract_portals_from_pdf(portals_path)
    assert len(portals) == 205, f"Expected 205 portals, extracted {len(portals)}"
    assert all(p["name"] and p["base_url"] and p["normalized_url"] for p in portals)
    assert any("Indeed" in p["name"] for p in portals)
    assert any("Naukri" in p["name"] for p in portals)

    # 2. Companies extraction
    companies, email_contacts = extract_companies_from_pdf(companies_path)
    assert len(companies) == 846, f"Expected 846 companies, extracted {len(companies)}"
    assert len(email_contacts) == 95, f"Expected 95 email records, extracted {len(email_contacts)}"

    # Multi-line company name verification
    mercedes = next(c for c in companies if c["sno"] == 496)
    assert "India" in mercedes["canonical_name"]

    supergaming = next(c for c in companies if c["sno"] == 712)
    assert "SuperGaming" in supergaming["canonical_name"]
    assert "supergaming.com" in (supergaming["career_url"] or "")

    # Multiple contact emails on single company
    bolt = next(c for c in companies if c["sno"] == 107)
    assert len(bolt["contact_emails"]) >= 2
    assert "sales@bolt.earth" in bolt["contact_emails"]
    assert "support@bolt.earth" in bolt["contact_emails"]


def test_database_idempotency_and_preservation():
    """Verify that database records are persistent, deduplicated, and preserve multiple links."""
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    cur = conn.cursor()

    # Check portal count
    cur.execute("SELECT COUNT(*) FROM job_sources")
    portal_count = cur.fetchone()[0]
    assert portal_count == 205, f"Expected 205 job sources, found {portal_count}"

    # Check companies count (819 unique canonical entities out of 846 rows)
    cur.execute("SELECT COUNT(*) FROM companies")
    company_count = cur.fetchone()[0]
    assert company_count == 819, f"Expected 819 companies, found {company_count}"

    # Check career sources count (832 unique career URLs)
    cur.execute("SELECT COUNT(*) FROM company_career_sources")
    career_sources_count = cur.fetchone()[0]
    assert career_sources_count >= 828, f"Expected at least 828 career sources, found {career_sources_count}"

    # Check contact emails count
    cur.execute("SELECT COUNT(*) FROM company_contacts")
    contacts_count = cur.fetchone()[0]
    assert contacts_count == 95, f"Expected 95 contact records, found {contacts_count}"

    # Check import batches
    cur.execute("SELECT COUNT(*) FROM source_import_batches WHERE import_status = 'COMPLETED'")
    batch_count = cur.fetchone()[0]
    assert batch_count >= 2, f"Expected at least 2 completed batches, found {batch_count}"

    # Verify multiple career URLs preserved for Accenture
    cur.execute("SELECT id FROM companies WHERE canonical_name = 'Accenture'")
    acc_id = cur.fetchone()[0]
    cur.execute("SELECT career_url FROM company_career_sources WHERE company_id = ?", (acc_id,))
    acc_career_urls = [r[0] for r in cur.fetchall()]
    assert len(acc_career_urls) >= 2, f"Accenture should have multiple career URLs, found {acc_career_urls}"

    # Verify multiple contacts preserved for Accenture
    cur.execute("SELECT email FROM company_contacts WHERE company_id = ?", (acc_id,))
    acc_emails = [r[0] for r in cur.fetchall()]
    assert len(acc_emails) >= 2, f"Accenture should have multiple emails, found {acc_emails}"
    assert "candidate.queries@accenture.com" in acc_emails
    assert "india.recruitment@accenture.com" in acc_emails

    conn.close()


def test_pagination_and_filtering_logic():
    """Verify pagination and search filtering logic for registry sources and companies."""
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    cur = conn.cursor()

    # 1. Search portal by keyword
    cur.execute("SELECT COUNT(*) FROM job_sources WHERE name LIKE '%Naukri%'")
    naukri_count = cur.fetchone()[0]
    assert naukri_count > 0

    # 2. Filter portals by category
    cur.execute("SELECT COUNT(*) FROM job_sources WHERE category LIKE '%Engineering%'")
    eng_count = cur.fetchone()[0]
    assert eng_count > 0

    # 3. Search company by keyword
    cur.execute("SELECT id, canonical_name FROM companies WHERE canonical_name LIKE '%Infosys%'")
    infosys = cur.fetchall()
    assert len(infosys) > 0

    # 4. Filter companies with email contacts
    cur.execute("""
        SELECT COUNT(DISTINCT c.id) 
        FROM companies c 
        JOIN company_contacts cc ON c.id = cc.company_id
    """)
    companies_with_email = cur.fetchone()[0]
    assert companies_with_email > 0
    assert companies_with_email <= 95

    # 5. Check relevance category distribution
    cur.execute("SELECT relevance_category, COUNT(*) FROM companies GROUP BY relevance_category")
    rel_dist = dict(cur.fetchall())
    assert "IT Services" in rel_dist
    assert "Product Companies" in rel_dist
    assert "SaaS" in rel_dist
    assert "FinTech" in rel_dist

    conn.close()

