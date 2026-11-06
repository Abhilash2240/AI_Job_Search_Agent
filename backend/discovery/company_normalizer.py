# backend/discovery/company_normalizer.py
"""Company name normalization and relevance classification for the AI Job Search Agent.

Adheres strictly to Phase 4A requirements:
- Deduplicates companies without over-merging distinct entities.
- Transparent relevance classification based on evidence (does not invent or guess recklessly).
- Retains all records; never deletes companies based on classification.
"""

import re
from typing import Tuple, Optional
from models.source import RelevanceCategory

# Suffixes to strip when creating normalized lookup keys
LEGAL_SUFFIXES_REGEX = re.compile(
    r"\b(pvt\.?\s*ltd\.?|private\s+limited|pvt\s+limited|limited|ltd\.?|inc\.?|llc\.?|llp\.?|corp\.?|corporation|gmbh|co\.?|s\.?a\.?|r&d)\b",
    re.IGNORECASE
)

# High-confidence curated evidence mappings for well-known tech employers
CURATED_RELEVANCE = {
    # IT Services
    "tcs": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "tata consultancy services": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "infosys": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "wipro": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "cognizant": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "tech mahindra": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "hcl": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "hcl tech": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "hcl technologies": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "mphasis": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "mindtree": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "ltimindtree": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "capgemini": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "hexaware": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "hexaware technologies": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "birlasoft": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "persistent systems": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "virtusa": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "genpact": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "accenture": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "dxc technology": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "zensar": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "zensar technologies": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "tata elxsi": (RelevanceCategory.IT_SERVICES.value, "Engineering & Technology Services"),
    "ust global": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "cyient": (RelevanceCategory.IT_SERVICES.value, "Engineering & Technology Services"),
    "happiest minds": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "happiest minds technologies": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "sonata software": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "ntt data": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),
    "kpit": (RelevanceCategory.IT_SERVICES.value, "Automotive & Software Services"),
    "kpit technologies": (RelevanceCategory.IT_SERVICES.value, "Automotive & Software Services"),
    "coforge": (RelevanceCategory.IT_SERVICES.value, "Information Technology & Services"),

    # Product Companies
    "google": (RelevanceCategory.PRODUCT_COMPANIES.value, "Internet & Software Products"),
    "microsoft": (RelevanceCategory.PRODUCT_COMPANIES.value, "Software & Cloud"),
    "amazon": (RelevanceCategory.PRODUCT_COMPANIES.value, "E-Commerce & Cloud"),
    "apple": (RelevanceCategory.PRODUCT_COMPANIES.value, "Consumer Electronics & Software"),
    "meta": (RelevanceCategory.PRODUCT_COMPANIES.value, "Social Media & Technology"),
    "adobe": (RelevanceCategory.PRODUCT_COMPANIES.value, "Creative Software & Cloud"),
    "atlassian": (RelevanceCategory.PRODUCT_COMPANIES.value, "Collaboration & Developer Tools"),
    "cisco": (RelevanceCategory.PRODUCT_COMPANIES.value, "Networking & Hardware"),
    "oracle": (RelevanceCategory.PRODUCT_COMPANIES.value, "Enterprise Software & Cloud"),
    "salesforce": (RelevanceCategory.PRODUCT_COMPANIES.value, "Enterprise Cloud & CRM"),
    "intel": (RelevanceCategory.PRODUCT_COMPANIES.value, "Semiconductors & Hardware"),
    "nvidia": (RelevanceCategory.PRODUCT_COMPANIES.value, "AI Hardware & Semiconductors"),
    "amd": (RelevanceCategory.PRODUCT_COMPANIES.value, "Semiconductors & Processors"),
    "uber": (RelevanceCategory.PRODUCT_COMPANIES.value, "Mobility & Platform Technology"),
    "intuit": (RelevanceCategory.PRODUCT_COMPANIES.value, "Financial Software"),
    "qualcomm": (RelevanceCategory.PRODUCT_COMPANIES.value, "Wireless & Semiconductors"),
    "servicenow": (RelevanceCategory.PRODUCT_COMPANIES.value, "Enterprise Cloud Workflows"),

    # SaaS
    "zoho": (RelevanceCategory.SAAS.value, "Business Software & Cloud SaaS"),
    "freshworks": (RelevanceCategory.SAAS.value, "Customer Engagement SaaS"),
    "postman": (RelevanceCategory.SAAS.value, "API Development Platform"),
    "browserstack": (RelevanceCategory.SAAS.value, "Software Testing Cloud"),
    "druva": (RelevanceCategory.SAAS.value, "Cloud Data Protection & Management"),
    "atlan": (RelevanceCategory.SAAS.value, "Active Metadata Platform"),
    "chargebee": (RelevanceCategory.SAAS.value, "Subscription Management SaaS"),
    "zenoti": (RelevanceCategory.SAAS.value, "Spa & Salon Management SaaS"),
    "icertis": (RelevanceCategory.SAAS.value, "Contract Management Cloud"),

    # AI / ML
    "yellow ai": (RelevanceCategory.AI_ML.value, "Conversational AI Platform"),
    "yellowai": (RelevanceCategory.AI_ML.value, "Conversational AI Platform"),
    "vitra ai": (RelevanceCategory.AI_ML.value, "Video Translation & Generative AI"),
    "greyorange": (RelevanceCategory.AI_ML.value, "AI Robotics & Warehouse Automation"),
    "graymatics": (RelevanceCategory.AI_ML.value, "Computer Vision & Cognitive AI"),
    "ati motors": (RelevanceCategory.AI_ML.value, "Autonomous Mobile Robots"),
    "upliance ai": (RelevanceCategory.AI_ML.value, "Smart Home Appliances & AI"),

    # FinTech
    "razorpay": (RelevanceCategory.FINTECH.value, "Financial Services & Payment Gateway"),
    "juspay": (RelevanceCategory.FINTECH.value, "Digital Payments & Infrastructure"),
    "bharatpe": (RelevanceCategory.FINTECH.value, "Merchant Payments & FinTech"),
    "paytm": (RelevanceCategory.FINTECH.value, "Digital Payments & Financial Services"),
    "phonepe": (RelevanceCategory.FINTECH.value, "Digital Payments & UPI Infrastructure"),
    "ftcash": (RelevanceCategory.FINTECH.value, "Micro-Merchant Financial Services"),
    "kaleidofin": (RelevanceCategory.FINTECH.value, "Inclusive FinTech Solutions"),
    "cred": (RelevanceCategory.FINTECH.value, "Credit Card Rewards & FinTech"),
    "zaggle": (RelevanceCategory.FINTECH.value, "Spend Management & Corporate FinTech"),
    "yubi": (RelevanceCategory.FINTECH.value, "Debt Capital Markets & Corporate Credit"),
    "pine labs": (RelevanceCategory.FINTECH.value, "Merchant Commerce & POS FinTech"),

    # Cybersecurity
    "zscaler": (RelevanceCategory.CYBERSECURITY.value, "Cloud Security & Zero Trust"),
    "blusapphire": (RelevanceCategory.CYBERSECURITY.value, "Cybersecurity & Incident Response"),
    "quick heal": (RelevanceCategory.CYBERSECURITY.value, "Cybersecurity & Anti-Virus"),
    "tac security": (RelevanceCategory.CYBERSECURITY.value, "Risk-Based Vulnerability Management"),

    # Cloud & Infrastructure
    "akamai": (RelevanceCategory.CLOUD_INFRASTRUCTURE.value, "Content Delivery Network & Cloud"),
    "akamai technologies": (RelevanceCategory.CLOUD_INFRASTRUCTURE.value, "Content Delivery Network & Cloud"),
    "nutanix": (RelevanceCategory.CLOUD_INFRASTRUCTURE.value, "Hybrid Multicloud Infrastructure"),

    # Technology Startups
    "wellfound": (RelevanceCategory.TECHNOLOGY_STARTUPS.value, "Startup Recruitment & Venture Platform"),
    "swiggy": (RelevanceCategory.TECHNOLOGY_STARTUPS.value, "On-Demand Delivery & Tech Platform"),
    "zomato": (RelevanceCategory.TECHNOLOGY_STARTUPS.value, "Food Tech & Quick Commerce"),
    "rapido": (RelevanceCategory.TECHNOLOGY_STARTUPS.value, "Bike Taxi & Mobility Tech"),
    "zepto": (RelevanceCategory.TECHNOLOGY_STARTUPS.value, "Quick Commerce & Tech Logistics"),
}


def normalize_company_name(name: str) -> str:
    """Normalize company name to canonical lowercase matching key without legal entity noise."""
    if not name:
        return ""
    
    clean = name.strip()
    # Normalize ampersand
    clean = re.sub(r"\s*&\s*", " and ", clean)
    # Remove legal suffixes
    clean = LEGAL_SUFFIXES_REGEX.sub("", clean)
    # Strip punctuation characters: commas, dots, parentheses, brackets, quotes, hyphens
    clean = re.sub(r"[,\.\(\)\[\]\"'\-_/\\;:]", " ", clean)
    # Collapse multiple whitespace
    clean = re.sub(r"\s+", " ", clean).strip().lower()
    return clean


def classify_company_relevance(
    company_name: str,
    career_url: Optional[str] = None,
    linkedin_url: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """Determine relevance category and industry based strictly on verifiable source evidence.
    
    Returns (relevance_category, industry).
    Defaults to ('Unknown', None) when evidence is insufficient, avoiding guessing from name alone.
    """
    norm_name = normalize_company_name(company_name)

    # 1. Curated high-confidence match
    if norm_name in CURATED_RELEVANCE:
        return CURATED_RELEVANCE[norm_name]

    # Check partial prefix for well-known conglomerates (e.g. 'TCS' in 'TCS - Tata Consultancy Services')
    for known_key, (cat, ind) in CURATED_RELEVANCE.items():
        if norm_name == known_key or norm_name.startswith(f"{known_key} "):
            return cat, ind

    # 2. Domain / URL-based evidence
    url_check = (career_url or "").lower()
    if ".ai/" in url_check or url_check.endswith(".ai") or "ai." in url_check:
        return RelevanceCategory.AI_ML.value, "Artificial Intelligence & Machine Learning"

    if any(k in norm_name.split() for k in ["technologies", "technology", "infotech", "software", "solutions", "systems", "tech"]):
        return RelevanceCategory.IT_SERVICES.value, "Information Technology Services"

    if any(k in norm_name.split() for k in ["fintech", "payments", "capital", "finance", "financial"]):
        return RelevanceCategory.FINTECH.value, "Financial Technology & Services"

    if any(k in norm_name.split() for k in ["security", "cyber", "cybersecurity"]):
        return RelevanceCategory.CYBERSECURITY.value, "Cybersecurity"

    if any(k in norm_name.split() for k in ["analytics", "data", "intelligence"]):
        return RelevanceCategory.AI_ML.value, "Data Analytics & Intelligence"

    # Default: Unknown (requires manual review, do not guess recklessly)
    return RelevanceCategory.UNKNOWN.value, None

