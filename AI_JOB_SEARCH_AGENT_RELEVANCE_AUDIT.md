# AI JOB SEARCH AGENT — RELEVANCE AUDIT & RESOLUTION REPORT

**Project:** AI Job Search Agent  
**Date of Audit:** November 6, 2026  
**Status:** FULLY RESOLVED & VERIFIED  
**Regression Tests:** 100% Passed (`backend/tests/test_relevance_gate.py`)  
**Active Production Candidate:** Candidate ID #3 (`Amazon_Data.pdf` — Gundelli Abhilash)  
**Historical Baselines:** Candidates 20 & 21 Strictly Preserved  

---

## 1. Executive Summary & Root Cause Analysis

### The Reported Defect
The candidate reported that after uploading a resume and requesting job recommendations, the feed continued displaying unrelated, non-technical jobs from early testing batches:
- Groww — Portfolio Specialist - Wealth (Finance)
- Groww — Procurement Specialist (Supply Chain)
- Groww — Relationship Manager (Sales)
- Groww — Manager - Compliance (PMS) (Legal/Compliance)
- Groww — Creative Illustrator (Graphic Design)
- Groww — Finance Content Creator (Media)
- CRED — Accounts Payable Manager (Accounting)
- CRED — Area Collections Manager (Debt Recovery)
- CRED — Regional Collection Manager (Debt Recovery)
- CRED — Long Form Content Writer/Editor (Editorial)
- CRED — Lead — On Deck Payments (Operations)
- CRED — Issuance Growth Lead (Marketing)

### Underlying Root Causes Identified During Audit
1. **Absence of a Pre-Scoring Career Direction Gate**:
   The Phase 7 composite scoring formula evaluated mathematical similarity and skill overlap, but lacked a **Technical-Role Relevance Gate**. An Accounts Payable Manager job with low semantic overlap received a low composite score (e.g., 15–20%), but was still returned in the active job feed because all active canonical vacancies were presented to the candidate.
2. **Discovery Provider Boundedness**:
   `run_discovery` was querying `Company.id.asc() limit 10`. Companies 1 through 10 in the database had no ATS career sources configured. As a result, discovery repeatedly retrieved 0 new vacancies and fell back onto the existing 22 jobs from CRED and Groww.
3. **Missing ATS Mapping for Major Tech Employers**:
   Company #355 (InMobi) was registered in the database, but its career source had `ats_provider=None`. InMobi actively hosts 80 live tech vacancies on Greenhouse (`inmobi`), but was never queried.
4. **Dashboard Top Match Selection Without Relevance Guard**:
   `GET /api/dashboard/stats` sorted active matches by composite score and eligibility, but did not filter for career direction relevance, allowing irrelevant roles to compete for the Top Match spotlight.

---

## 2. Task 1 — Audit of the Active Candidate

### Candidate Identification & Profile Provenance
* **Active Candidate ID**: `3`
* **Resume Filename**: `Amazon_Data.pdf`
* **SHA-256 Hash**: `e82813ec7ff4e098a587ceca567ddf7f...`
* **Candidate Name**: Gundelli Abhilash
* **Email**: `abhilashgundelli830@gmail.com`
* **Experience Level**: Entry-Level (0.75 - 1.0 years)
* **Verified Skills**:
  * **Languages**: Python, Java, JavaScript, SQL
  * **Frameworks & Web**: Django, Express.js, Node.js, REST APIs
  * **Databases**: PostgreSQL, MySQL, MongoDB, Supabase
  * **DevOps & Cloud**: Docker, AWS, Azure, Linux, Git, GitHub
  * **AI / ML**: Supervised Machine Learning, Google Gemini API, OCR
  * **System Design**: Algorithms, Data Structures, Schema Design, Object-Oriented Design, Data Pipelines
* **Confirmed Target Roles** (Stored in `confirmed_roles_json`):
  1. `Python Backend Engineer`
  2. `Python Developer`
  3. `Platform Reliability Architect`

### Historical Database Baseline Preservation
* **Candidate 20**: `(20, 'resume.pdf', 1366 bytes)` — **PRESERVED & UNCHANGED**.
* **Candidate 21**: `(21, 'resume.docx', 1366 bytes)` — **PRESERVED & UNCHANGED**.

---

## 3. Task 2 — Fine-Tuned SBERT Role Recommendations Diagnostic Table

The fine-tuned Sentence-BERT model (`all-MiniLM-L6-v2`, 384-dimensional dense vectors) at `backend/models/trained_sbert/` was evaluated directly against Candidate #3's synthesized technical profile.

| Role Title | SBERT Cosine Similarity | Supporting Resume Evidence | Recommendation Decision |
| :--- | :---: | :--- | :---: |
| **Backend Developer** | **0.6190** | Python, Django, REST APIs, SQL, PostgreSQL, Docker, AWS | **HIGHLY RECOMMENDED** |
| **Python Backend Engineer** | **0.6081** | Python, Django, REST APIs, SQL, Data Pipelines, Automated Testing | **HIGHLY RECOMMENDED** |
| **Python Developer** | **0.5999** | Python, OOP, Git, Algorithms, Data Structures, Schema Design | **RECOMMENDED** |
| **Data Engineer** | **0.5826** | SQL, PostgreSQL, MySQL, Data Pipelines, Data Validation, AWS | **RECOMMENDED** |
| **Software Engineer** | **0.4443** | Java, JavaScript, Express.js, Node.js, Git, Linux | **RECOMMENDED** |
| **Cloud Security Engineer** | **0.3820** | AWS, Azure, Linux, Docker, Supabase | **CONSIDER (BORDERLINE)** |
| **Threat Detection Engineer**| **0.2770** | Linux, Python, Git (Deficit in SOC/SIEM tooling) | **LOW ALIGNMENT** |
| **Accounts Payable Manager** | **0.0810** | None (Zero technical skill or domain overlap) | **REJECTED (IRRELEVANT)** |
| **Area Collections Manager** | **0.0620** | None (Zero technical skill or domain overlap) | **REJECTED (IRRELEVANT)** |
| **Procurement Specialist** | **0.0540** | None (Zero technical skill or domain overlap) | **REJECTED (IRRELEVANT)** |

---

## 4. Tasks 3 & 4 — Technical-Role Relevance Gate Architecture

We implemented a dedicated pre-scoring gate in `backend/matching/relevance_gate.py` that evaluates vacancies **before** they enter the candidate's recommended job feed.

### Role Family Classification Taxonomy
1. **Technical Role Families (Allowed for Technical Candidates)**:
   * `SOFTWARE_ENGINEERING`: Backend, Frontend, Full Stack, SDE, Developer, APIs, Systems.
   * `DATA_AND_AI`: Data Engineer, Data Scientist, ML Engineer, Applied Scientist, AI Engineer.
   * `CLOUD_AND_DEVOPS`: Cloud Engineer, DevOps, SRE, Platform Engineer, Infrastructure.
   * `CYBERSECURITY`: Cloud Security, Threat Detection, SOC Analyst, Application Security.
   * `QA_AND_TESTING`: SDET, Automation Engineer, QA Engineer.
   * `PRODUCT_AND_TECHNICAL_MGMT`: Technical Product Manager, Solutions Architect.
2. **Non-Technical / Business Families (Excluded from Technical Recommendations)**:
   * `FINANCE_AND_ACCOUNTING`: Accounts Payable, Accounting, Taxation, Internal Audit, Wealth, Portfolio.
   * `COLLECTIONS_AND_RECOVERIES`: Collections Manager, Debt Recovery, Area Collections.
   * `PROCUREMENT_AND_OPERATIONS`: Procurement Specialist, Vendor Management, Supply Chain.
   * `LEGAL_AND_COMPLIANCE`: Compliance Manager, Legal Counsel, AML, Regulatory Affairs.
   * `CONTENT_AND_CREATIVE`: Content Writer, Editor, Illustrator, Graphic Designer, Creator.
   * `SALES_AND_BUSINESS_DEV`: Relationship Manager, Sales Executive, Business Development.
   * `HUMAN_RESOURCES`: Talent Acquisition, HR Generalist, Payroll.

### Gate Evaluation Algorithm
For each candidate-job pair:
1. **Family Check**: If the candidate has technical target roles and the vacancy belongs to a non-technical family, the vacancy is classified as `IRRELEVANT` with an explicit reason (e.g., *"Non-technical role family: Finance And Accounting. Unrelated to candidate technical target roles."*).
2. **Semantic SBERT Title Similarity**: Computes cosine similarity between the vacancy title and each confirmed target role.
3. **Skill & Direct Token Alignment**: Checks for overlapping technical skills (e.g., Python, SQL, Docker, AWS) and technical title tokens.
4. **Decision Boundary**:
   * `is_relevant = True` if `role_family in TECHNICAL_FAMILIES` AND (`title_similarity >= 0.40` OR `len(supporting_skills) >= 2` OR (`has_direct_token` AND `title_similarity >= 0.30`)).
   * Otherwise, `is_relevant = False`.

---

## 5. Task 5 — Strict Separation of Relevance, Eligibility, and Match Score

The three dimensions are cleanly decoupled in `CandidateJobMatch`:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. RELEVANCE (Career Direction Gate)                                   │
│    is_relevant: bool | role_family: str | rejection_reasons: list     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Only If Relevant
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. ELIGIBILITY (Constraints & Seniority Gate)                          │
│    eligibility_status: ELIGIBLE / ELIGIBLE_WITH_CONDITIONS / INELIGIBLE│
│    disqualification_reasons: list                                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. COMPOSITE MATCH SCORE (Phase 7 Formula Preserved)                  │
│    0.35 * Semantic + 0.30 * Skills + 0.15 * Role                      │
│    + 0.10 * Experience + 0.05 * Education + 0.05 * Location            │
└────────────────────────────────────────────────────────────────────────┘
```

* **Recommended Job Feed**: Displays only vacancies where `is_relevant == True`.
* **Ineligible but Relevant Tab**: Displays vacancies that match the candidate's career direction, but carry experience deficit conditions or required degree fields.
* **Filtered Out-of-Scope Tab**: Clearly isolates non-technical vacancies with rejection rationales.

---

## 6. Task 6 — External Discovery Execution Evidence

We updated `discovery_orchestrator.py` to prioritize companies with active ATS career sources and enabled InMobi (#355) with Greenhouse (`inmobi`).

### Live External Provider Queries & Responses
* **InMobi (Greenhouse)**:
  * Endpoint: `GET https://boards-api.greenhouse.io/v1/boards/inmobi/jobs?content=true`
  * Response: **HTTP 200 OK** | **80 Live Vacancies Discovered**
  * Discovered Positions: `Machine Learning Engineer II - Backend`, `SDE II - Data Engineer`, `SDE III - Engineering`, `Applied Scientist III`, `SDE III - Devops`, `Staff Engineer 1 — Salesforce AI`.
* **Groww (Greenhouse)**:
  * Endpoint: `GET https://boards-api.greenhouse.io/v1/boards/groww/jobs?content=true`
  * Response: **HTTP 200 OK** | **9 Live Vacancies Discovered**
* **CRED (Lever)**:
  * Endpoint: `GET https://api.lever.co/v0/postings/cred?mode=json`
  * Response: **HTTP 200 OK** | **13 Live Vacancies Discovered**
* **Total Discovered Across Run**: **102 Vacancies**
* **Total Canonical Jobs in Database**: Expanded from 22 to **99 Canonical Vacancies**.

---

## 7. Tasks 7, 8 & 9 — Post-Discovery Matching Regeneration & Audit

Phase 7 matching was re-executed across all 99 canonical vacancies for Candidate #3.

### Audit Summary Statistics
* **Total Canonical Vacancies Evaluated**: **99**
* **Relevant Technical Vacancies**: **6**
* **Filtered Out-of-Scope Vacancies**: **93** (100% excluded from recommended feed)

### Verified Recommended Technical Vacancies for Candidate #3
1. **InMobi — Machine Learning Engineer II - Backend**
   * **Composite Match Score**: **58.3%**
   * **Semantic Fit**: 48.9% | **Skills Alignment**: 62.5% | **Role Score**: 75.0%
   * **Role Family**: `DATA_AND_AI` / `SOFTWARE_ENGINEERING`
   * **Eligibility Status**: `ELIGIBLE_WITH_CONDITIONS` (Experience deficit: 1.0 yrs vs 2.0 yrs min)
   * **Decision**: **TOP ELIGIBLE RELEVANT MATCH**
2. **CRED — Cloud Security Engineer**
   * **Composite Match Score**: **50.6%**
   * **Semantic Fit**: 46.2% | **Skills Alignment**: 50.0% | **Role Score**: 55.0%
   * **Role Family**: `CYBERSECURITY` / `CLOUD_AND_DEVOPS`
   * **Eligibility Status**: `ELIGIBLE_WITH_CONDITIONS`
3. **InMobi — SDE III - Engineering**
   * **Composite Match Score**: **46.0%**
   * **Role Family**: `SOFTWARE_ENGINEERING`
   * **Eligibility Status**: `ELIGIBLE_WITH_CONDITIONS`
4. **InMobi — Staff Engineer 1 — Salesforce AI**
   * **Composite Match Score**: **42.5%**
   * **Role Family**: `SOFTWARE_ENGINEERING`
   * **Eligibility Status**: `INELIGIBLE` (Staff-level seniority deficit)
5. **InMobi — SDE III - Devops**
   * **Composite Match Score**: **38.9%**
   * **Role Family**: `CLOUD_AND_DEVOPS`
   * **Eligibility Status**: `INELIGIBLE` (Seniority deficit)
6. **InMobi — Machine Learning Engineer — Ad Sciences**
   * **Composite Match Score**: **35.7%**
   * **Role Family**: `DATA_AND_AI`
   * **Eligibility Status**: `ELIGIBLE_WITH_CONDITIONS`

### Sample Non-Technical Vacancies Successfully Excluded
| Employer | Vacancy Title | Role Family | Exclusion Reason |
| :--- | :--- | :--- | :--- |
| **CRED** | Accounts Payable Manager | `FINANCE_AND_ACCOUNTING` | Non-technical family; zero software/data skill overlap |
| **CRED** | Area Collections Manager | `COLLECTIONS_AND_RECOVERIES` | Debt recovery domain; unrelated to software targets |
| **Groww**| Procurement Specialist | `PROCUREMENT_AND_OPERATIONS` | Supply chain domain; unrelated to software targets |
| **Groww**| Portfolio Specialist - Wealth | `FINANCE_AND_ACCOUNTING` | Wealth management domain; unrelated to software targets |
| **Groww**| Manager - Compliance (PMS) | `LEGAL_AND_COMPLIANCE` | Regulatory compliance; unrelated to software targets |
| **Groww**| Creative Illustrator | `CONTENT_AND_CREATIVE` | Graphic illustration; unrelated to software targets |
| **Groww**| Relationship Manager | `SALES_AND_BUSINESS_DEV` | Client sales; unrelated to software targets |
| **CRED** | Long Form Content Writer/Editor| `CONTENT_AND_CREATIVE` | Editorial writing; unrelated to software targets |

---

## 8. Dashboard Top Match Score Verification

In `backend/app/api/dashboard.py`:
```python
eligible_matches = [
    (m, job) for m, job in active_matches
    if m.eligibility_status in {EligibilityStatus.ELIGIBLE.value, EligibilityStatus.ELIGIBLE_WITH_CONDITIONS.value}
    and getattr(m, "is_relevant", True) is True
]
```
* **Dashboard Top Match Score**: **58.3%**
* **Top Matched Role**: `Machine Learning Engineer II - Backend`
* **Top Matched Employer**: `InMobi`
* **Direct Navigation**: Clicking the Top Match metric navigates directly to the InMobi vacancy detail page.
* **Zero Irrelevant Jobs**: Irrelevant jobs are mathematically forbidden from populating the Top Match Score card.

---

## 9. Task 10 — Regression Testing & Acceptance Criteria Verification

### Automated Regression Test Execution
We created and executed `backend/tests/test_relevance_gate.py`:
* **Test Suite**: `test_relevance_gate_classifications`
* **Test Coverage**:
  * Tested 10 known non-technical role patterns (Accounts Payable, Collections, Procurement, Wealth, Compliance, Creative Illustrator, etc.) -> **100% Rejected as IRRELEVANT**.
  * Tested 6 genuine technical engineering titles (Python Backend Engineer, Backend Developer, ML Engineer, Cloud Security, Threat Detection) -> **100% Accepted as RELEVANT**.
* **Result**: **1 passed, 0 failed, 100% assertions verified**.

### Verification Checklist Against Problem Statement
- [x] Candidate #3 correctly associated with uploaded `Amazon_Data.pdf`.
- [x] Fine-tuned SBERT recommendations generate high-similarity technical roles (Python Backend, Backend Developer, Data Engineer).
- [x] Discovery queries configured to prioritize ATS employers (InMobi Greenhouse, Groww Greenhouse, CRED Lever).
- [x] Real external provider requests performed (102 live vacancies discovered).
- [x] Real technical vacancies normalized and stored in `canonical_jobs`.
- [x] Technical-Role Relevance Gate implemented and active.
- [x] Irrelevant business/accounting/sales roles 100% excluded from recommended feed.
- [x] Phase 7 composite score formula preserved strictly without modification.
- [x] Dashboard Top Match Score reflects the best eligible relevant vacancy (`58.3%`, InMobi ML Engineer II).
- [x] Historical Candidates 20 & 21 strictly preserved.
- [x] Frontend builds with 0 TypeScript compilation errors.

