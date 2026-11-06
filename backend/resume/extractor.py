import re
from typing import Dict, List, Optional, Any, Tuple
from schemas.candidate import (
    PersonalInfo,
    EducationItem,
    SkillsCategorized,
    ExperienceItem,
    ProjectItem,
    InternshipItem,
    CertificationItem,
)

# Skill Taxonomy definition
SKILL_TAXONOMY = {
    "programming_languages": [
        "python", "java", "c++", "c#", "c", "javascript", "typescript", "golang", "go",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "dart", "bash", "shell",
        "html", "css", "html5", "css3", "sass", "matlab"
    ],
    "frameworks": [
        "react", "react.js", "reactjs", "angular", "angularjs", "vue", "vue.js", "next.js", "nextjs",
        "nuxt", "django", "flask", "fastapi", "spring", "spring boot", "express", "express.js",
        "node.js", "nodejs", "asp.net", ".net", "ruby on rails", "rails", "flutter", "react native",
        "tailwind", "tailwind css", "bootstrap", "jquery", "svelte"
    ],
    "databases": [
        "postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite", "oracle",
        "cassandra", "elasticsearch", "dynamodb", "mariadb", "neo4j", "couchdb",
        "firestore", "supabase", "snowflake", "bigquery"
    ],
    "tools": [
        "git", "github", "gitlab", "docker", "kubernetes", "k8s", "aws", "amazon web services",
        "gcp", "google cloud", "azure", "microsoft azure", "linux", "unix", "jenkins", "terraform",
        "ansible", "ci/cd", "jira", "kafka", "rabbitmq", "nginx", "postman", "prometheus", "grafana",
        "circleci", "helm", "argo", "datadog", "automated testing", "test automation", "data validation",
        "quality engineering", "reliability testing"
    ],
    "ai_ml": [
        "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", "numpy", "scipy",
        "opencv", "hugging face", "transformers", "sentence-transformers", "sbert", "bert",
        "langchain", "llamaindex", "nlp", "natural language processing", "computer vision",
        "deep learning", "machine learning", "llm", "llms", "large language models", "generative ai",
        "genai", "xgboost", "lightgbm", "spacy", "nltk", "matplotlib", "seaborn",
        "gemini", "google gemini", "gemini api", "rag", "retrieval-augmented generation",
        "embeddings", "semantic search", "ai agents", "model evaluation", "f1-score", "roc-auc",
        "precision/recall", "supervised machine learning", "ocr"
    ],
    "other": [
        "rest api", "restful apis", "rest apis", "graphql", "microservices", "agile", "scrum",
        "unit testing", "system design", "data structures", "algorithms", "complexity analysis",
        "object-oriented design", "object-oriented programming", "ood", "oop",
        "dbms", "database management systems", "schema design", "data pipelines", "data pipeline",
        "data quality", "financial markets", "websocket", "grpc", "oauth", "jwt"
    ]
}

# Skill canonical name mapping for normalization
CANONICAL_SKILL_NAMES = {
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "c": "C",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "r": "R",
    "sql": "SQL",
    "dart": "Dart",
    "bash": "Bash",
    "shell": "Shell",
    "html": "HTML5",
    "html5": "HTML5",
    "css": "CSS3",
    "css3": "CSS3",
    "sass": "SASS",
    "matlab": "MATLAB",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "angular": "Angular",
    "angularjs": "Angular",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "nuxt": "Nuxt.js",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "spring": "Spring",
    "spring boot": "Spring Boot",
    "express": "Express.js",
    "express.js": "Express.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "asp.net": "ASP.NET",
    ".net": ".NET",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    "flutter": "Flutter",
    "react native": "React Native",
    "tailwind": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "jquery": "jQuery",
    "svelte": "Svelte",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "oracle": "Oracle",
    "cassandra": "Cassandra",
    "elasticsearch": "Elasticsearch",
    "dynamodb": "DynamoDB",
    "mariadb": "MariaDB",
    "neo4j": "Neo4j",
    "couchdb": "CouchDB",
    "firestore": "Firestore",
    "supabase": "Supabase",
    "snowflake": "Snowflake",
    "bigquery": "BigQuery",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "linux": "Linux",
    "unix": "Unix",
    "jenkins": "Jenkins",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "ci/cd": "CI/CD",
    "jira": "Jira",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "nginx": "Nginx",
    "postman": "Postman",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "circleci": "CircleCI",
    "helm": "Helm",
    "argo": "ArgoCD",
    "datadog": "Datadog",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scipy": "SciPy",
    "opencv": "OpenCV",
    "hugging face": "Hugging Face",
    "transformers": "Transformers",
    "sentence-transformers": "Sentence-Transformers",
    "sbert": "Sentence-BERT",
    "bert": "BERT",
    "langchain": "LangChain",
    "llamaindex": "LlamaIndex",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "computer vision": "Computer Vision",
    "deep learning": "Deep Learning",
    "machine learning": "Machine Learning",
    "llm": "LLMs",
    "llms": "LLMs",
    "large language models": "LLMs",
    "generative ai": "Generative AI",
    "genai": "Generative AI",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "spacy": "spaCy",
    "nltk": "NLTK",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "rest api": "REST APIs",
    "restful apis": "REST APIs",
    "rest apis": "REST APIs",
    "graphql": "GraphQL",
    "microservices": "Microservices",
    "agile": "Agile",
    "scrum": "Scrum",
    "unit testing": "Unit Testing",
    "system design": "System Design",
    "data structures": "Data Structures",
    "algorithms": "Algorithms",
    "oop": "OOP",
    "object-oriented programming": "OOP",
    "websocket": "WebSockets",
    "grpc": "gRPC",
    "oauth": "OAuth",
    "jwt": "JWT",
    "gemini": "Google Gemini API",
    "google gemini": "Google Gemini API",
    "gemini api": "Google Gemini API",
    "rag": "RAG",
    "retrieval-augmented generation": "RAG",
    "embeddings": "Embeddings",
    "semantic search": "Semantic Search",
    "ai agents": "AI Agents",
    "model evaluation": "Model Evaluation",
    "supervised machine learning": "Supervised Machine Learning",
    "ocr": "OCR",
    "automated testing": "Automated Testing",
    "test automation": "Automated Testing",
    "data validation": "Data Validation",
    "quality engineering": "Quality Engineering",
    "reliability testing": "Reliability Testing",
    "complexity analysis": "Complexity Analysis",
    "object-oriented design": "Object-Oriented Design",
    "ood": "Object-Oriented Design",
    "dbms": "DBMS",
    "database management systems": "DBMS",
    "schema design": "Schema Design",
    "data pipeline": "Data Pipelines",
    "data pipelines": "Data Pipelines",
    "data quality": "Data Quality",
    "financial markets": "Financial Markets"
}

# Common degree keywords and regex patterns
DEGREE_PATTERNS = [
    r"\b(B\.?Tech(?:nology)?|Bachelor of Technology)\b",
    r"\b(B\.?E\.?|Bachelor of Engineering)\b",
    r"\b(B\.?S\.?|B\.?Sc\.?|Bachelor of Science)\b",
    r"\b(B\.?C\.?A\.?|Bachelor of Computer Applications)\b",
    r"\b(M\.?Tech(?:nology)?|Master of Technology)\b",
    r"\b(M\.?E\.?|Master of Engineering)\b",
    r"\b(M\.?S\.?|M\.?Sc\.?|Master of Science)\b",
    r"\b(M\.?C\.?A\.?|Master of Computer Applications)\b",
    r"\b(M\.?B\.?A\.?|Master of Business Administration)\b",
    r"\b(Ph\.?D\.?|Doctor of Philosophy)\b",
    r"\b(Associate Degree|High School Diploma|Diploma)\b"
]

COMMON_MAJORS = [
    "Computer Science and Engineering", "Computer Science", "Information Technology",
    "Software Engineering", "Data Science", "Artificial Intelligence",
    "Machine Learning", "Electrical and Electronics Engineering", "Electronics and Communication",
    "Mechanical Engineering", "Civil Engineering", "Mathematics", "Statistics", "Physics"
]


def extract_email(text: str) -> Optional[str]:
    """Extract candidate email using regex."""
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """Extract candidate phone number."""
    # Look for standard international/domestic phone patterns
    pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    match = re.search(pattern, text)
    if match:
        val = match.group(0).strip()
        # Ensure it has at least 10 digits
        digits = re.sub(r"\D", "", val)
        if len(digits) >= 10:
            return val
    return None


TECH_LOCATION_BLACKLIST = {
    "python", "sql", "java", "javascript", "typescript", "c++", "c#", "c", "ruby", "golang", "go",
    "rust", "php", "swift", "kotlin", "scala", "html", "css", "react", "angular", "vue", "next",
    "django", "flask", "fastapi", "express", "node", "nodejs", "aws", "azure", "gcp", "docker",
    "kubernetes", "git", "github", "gitlab", "linux", "unix", "api", "apis", "rest", "rag", "ai",
    "ml", "ocr", "nlp", "llm", "llms", "etl", "jwt", "oauth", "dbms", "mongodb", "mysql", "postgres",
    "postgresql", "supabase", "redis", "kafka", "pandas", "numpy", "pytorch", "tensorflow",
    "automated", "testing", "quality", "engineering", "data", "validation"
}

KNOWN_GEOGRAPHIC_TERMS = {
    "india", "usa", "united states", "uk", "canada", "germany", "australia", "singapore",
    "telangana", "karnataka", "maharashtra", "tamil nadu", "andhra pradesh", "kerala",
    "gujarat", "delhi", "california", "texas", "new york", "washington", "illinois",
    "florida", "massachusetts", "colorado", "ohio", "georgia", "north carolina", "virginia",
    "bengaluru", "bangalore", "hyderabad", "warangal", "mumbai", "pune", "chennai", "kolkata",
    "san jose", "san francisco", "austin", "seattle", "boston", "chicago", "new york city"
}

# Standard US 2-letter state abbreviations
US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
}


def extract_location(text: str) -> Optional[str]:
    """Extract candidate personal geographic location from top header or contact info.
    
    Guarantees:
    - Never extracts technical skills (e.g. 'Python, SQL', 'API integration, RAG').
    - Distinguishes institution location from personal candidate location.
    - Matches only genuine geographic City, State/Country patterns.
    """
    head = text[:800]
    city_state_pattern = r"\b([A-Z][a-zA-Z\s.]+),\s*([A-Z]{2}|[A-Z][a-zA-Z\s.]+)\b"
    lines = head.split("\n")
    
    for line in lines[:8]:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        # Avoid lines that contain degrees, job titles, or resume section headers
        line_lower = line_clean.lower()
        if any(term in line_lower for term in [
            "engineer", "developer", "resume", "university", "college", "school",
            "experience", "education", "skills", "projects", "certifications",
            "coursework", "summary", "objective"
        ]):
            continue
            
        # Reject line immediately if it contains known technical skills
        tokens = [t.strip(",;|/()[]") for t in line_lower.split()]
        if any(tok in TECH_LOCATION_BLACKLIST for tok in tokens):
            continue
            
        match = re.search(city_state_pattern, line_clean)
        if match:
            city_part = match.group(1).strip()
            state_part = match.group(2).strip()
            
            # Check neither part is a blacklisted technical term
            city_tokens = [t.lower() for t in city_part.split()]
            state_tokens = [t.lower() for t in state_part.split()]
            if any(t in TECH_LOCATION_BLACKLIST for t in city_tokens + state_tokens):
                continue
                
            # Verify the second part is either a known US state abbreviation or geographic entity
            is_valid_geo = (
                state_part.upper() in US_STATE_CODES or
                state_part.lower() in KNOWN_GEOGRAPHIC_TERMS or
                city_part.lower() in KNOWN_GEOGRAPHIC_TERMS
            )
            
            if is_valid_geo:
                candidate_loc = f"{city_part}, {state_part}"
                if len(candidate_loc) < 50:
                    return candidate_loc
                    
    return None


def extract_name(text: str) -> Optional[str]:
    """Heuristic extraction of candidate name from the top lines of resume."""
    lines = text.split("\n")
    blacklist_words = {
        "resume", "curriculum", "vitae", "cv", "page", "phone", "email", "address",
        "objective", "summary", "profile", "contact", "education", "experience", "skills",
        "github", "linkedin", "portfolio", "http", "https", "www"
    }
    for line in lines[:8]:
        line_clean = line.strip()
        if not line_clean:
            continue
        # Check if line contains digits or email/url
        if "@" in line_clean or "http" in line_clean or any(c.isdigit() for c in line_clean):
            continue
        words = line_clean.split()
        if 2 <= len(words) <= 4:
            if not any(w.lower() in blacklist_words for w in words):
                # Ensure words are capitalized / alphabetic
                if all(re.match(r"^[A-Z][a-zA-Z\-'.]*$", w) for w in words):
                    return line_clean
    return None


def extract_personal_info(text: str) -> PersonalInfo:
    """Extract personal details."""
    return PersonalInfo(
        name=extract_name(text),
        email=extract_email(text),
        phone=extract_phone(text),
        location=extract_location(text)
    )


def extract_skills_section_text(text: str) -> str:
    """Extract the specific text block under Technical Skills headings."""
    skill_headers = [
        r"TECHNICAL\s+SKILLS?", r"SKILLS?(?:\s*(?:&|AND)\s*(?:TOOLS|TECHNOLOGIES)?)?",
        r"CORE\s+COMPETENCIES", r"TECHNOLOGIES?", r"AREAS?\s+OF\s+EXPERTISE",
        r"PROFESSIONAL\s+SKILLS?"
    ]
    pattern = rf"(?:^|\n)\s*(?:{'|'.join(skill_headers)})\s*[:\n]"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return ""
    start_pos = match.end()
    stopper_pattern = rf"(?:^|\n)\s*(?:{'|'.join(SECTION_STOPPERS)})\s*[:\n]"
    stop_match = re.search(stopper_pattern, text[start_pos:], re.IGNORECASE)
    if stop_match:
        return text[start_pos:start_pos + stop_match.start()]
    return text[start_pos:]


def extract_skills_with_sources(
    text: str,
    projects: Optional[List[ProjectItem]] = None,
    experience: Optional[List[ExperienceItem]] = None,
    education: Optional[List[EducationItem]] = None,
    certifications: Optional[List[CertificationItem]] = None,
) -> tuple[SkillsCategorized, Dict[str, List[str]], List[str]]:
    """Extract categorized technical skills with strict evidence source tracking.
    
    Guarantees:
    - Never invents candidate skills.
    - Preserves genuine project, experience, and certification evidence even if not in the skills list.
    - Eliminates unsupported skills that have zero evidence in the resume.
    - Generates provenance map: { skill_name.lower(): ['skills section', 'project: ReceiptFlow', ...] }.
    - Distinguishes verified skills from inferred/uncertain skills.
    """
    text_lower = text.lower()
    skills_sec_text = extract_skills_section_text(text).lower()
    
    categorized = {
        "programming_languages": set(),
        "frameworks": set(),
        "databases": set(),
        "tools": set(),
        "ai_ml": set(),
        "other": set()
    }
    skill_sources: Dict[str, List[str]] = {}
    inferred_skills: List[str] = []
    
    has_structured_sections = bool(skills_sec_text or projects or experience or certifications)
    
    for category, skill_list in SKILL_TAXONOMY.items():
        for skill in skill_list:
            escaped = re.escape(skill)
            pattern = rf"(?:^|[\s,;|/()\[\]]){escaped}(?:$|[\s,;|/()\[\]])"
            canonical = CANONICAL_SKILL_NAMES.get(skill, skill.title())
            sources = []
            
            # 1. Evidence in Skills Section
            if skills_sec_text and re.search(pattern, skills_sec_text):
                sources.append("skills section")
                
            # 2. Evidence in Verified Projects
            if projects:
                for p in projects:
                    p_name = p.name or "project"
                    p_text = f"{p_name} {' '.join(p.technologies)} {p.description or ''}".lower()
                    if re.search(pattern, p_text):
                        sources.append(f"project: {p_name}")
                        
            # 3. Evidence in Professional Experience
            if experience:
                for exp in experience:
                    comp = exp.company or "experience"
                    exp_text = f"{comp} {exp.job_title or ''} {exp.responsibilities or ''}".lower()
                    if re.search(pattern, exp_text):
                        sources.append(f"experience: {comp}")
                        
            # 4. Evidence in Education / Coursework
            if education:
                for edu in education:
                    univ = edu.university or "education"
                    edu_text = f"{edu.degree or ''} {edu.specialization or ''} {univ}".lower()
                    if re.search(pattern, edu_text):
                        sources.append(f"coursework: {univ}")
                        
            # 5. Evidence in Certifications
            if certifications:
                for cert in certifications:
                    cert_name = cert.name or "certification"
                    cert_text = f"{cert_name} {cert.issuer or ''}".lower()
                    if re.search(pattern, cert_text):
                        sources.append(f"certification: {cert_name}")
                        
            # 6. Fallback for raw text snippets (unit tests with isolated skills text)
            if not has_structured_sections:
                if re.search(pattern, text_lower):
                    sources.append("text evidence")
            elif not sources:
                # Check summary or achievements if not matched in core sections
                summary_match = re.search(rf"(?:^|\n)\s*(?:SUMMARY|OBJECTIVE|ACHIEVEMENTS?)\s*[:\n].*?(?=\n\s*[A-Z]{3,}|\Z)", text, re.IGNORECASE | re.DOTALL)
                if summary_match and re.search(pattern, summary_match.group(0).lower()):
                    sources.append("summary / achievements")
                    
            # Genuine verification rule: Keep only skills with proven evidence
            if sources:
                categorized[category].add(canonical)
                skill_sources[canonical.lower()] = sources

    # Identify potential inferred skills from tooling (e.g. Playwright -> E2E Testing, Clerk -> Auth Middleware)
    if "Playwright" in categorized["tools"] or any("playwright" in s for s in text_lower.split()):
        if "End-to-End Testing" not in categorized["tools"] and "End-to-End Testing" not in categorized["other"]:
            inferred_skills.append("End-to-End Testing")
    if "clerk" in text_lower and "JWT" in categorized["other"]:
        if "Authentication Middleware" not in categorized["other"]:
            inferred_skills.append("Authentication Middleware")

    skills_obj = SkillsCategorized(
        programming_languages=sorted(list(categorized["programming_languages"])),
        frameworks=sorted(list(categorized["frameworks"])),
        databases=sorted(list(categorized["databases"])),
        tools=sorted(list(categorized["tools"])),
        ai_ml=sorted(list(categorized["ai_ml"])),
        other=sorted(list(categorized["other"])),
    )
    
    return skills_obj, skill_sources, inferred_skills


def extract_skills(text: str) -> SkillsCategorized:
    """Extract categorized technical skills using taxonomy matching."""
    skills_obj, _, _ = extract_skills_with_sources(text)
    return skills_obj


EDUCATION_HEADERS = [
    r"EDUCATION(?:\s+AND\s+QUALIFICATIONS|\s+&\s+QUALIFICATIONS|\s+AND\s+TRAINING)?",
    r"ACADEMIC\s+DETAILS",
    r"EDUCATIONAL\s+QUALIFICATIONS?",
    r"ACADEMIC\s+QUALIFICATIONS?",
    r"ACADEMIC\s+BACKGROUND",
    r"ACADEMICS?"
]

SECTION_STOPPERS = [
    r"PROJECTS?", r"EXPERIENCE", r"WORK\s+EXPERIENCE", r"PROFESSIONAL\s+EXPERIENCE",
    r"TECHNICAL\s+SKILLS?", r"SKILLS?", r"CERTIFICATIONS?", r"CERTIFICATES?",
    r"ACHIEVEMENTS?", r"AWARDS?", r"PUBLICATIONS?", r"INTERNSHIPS?",
    r"SUMMARY", r"PROFESSIONAL\s+SUMMARY", r"OBJECTIVE"
]


def extract_education(text: str) -> List[EducationItem]:
    """Extract structured education entries supporting multiline formatting and varied headings."""
    header_rx = r"(?:^|\n)(?:" + "|".join(EDUCATION_HEADERS) + r")(?:\s*[:\n])"
    stopper_rx = r"\n(?=(?:" + "|".join(SECTION_STOPPERS) + r")\b|\Z)"
    
    sec_match = re.search(header_rx + r"(.*?)" + stopper_rx, text, re.IGNORECASE | re.DOTALL)
    if sec_match:
        edu_blocks = [sec_match.group(1).strip()]
    else:
        # Fallback to entire text if no explicit header
        edu_blocks = [text]
        
    education_entries: List[EducationItem] = []
    
    for block in edu_blocks:
        degrees_found = []
        for pat in DEGREE_PATTERNS:
            for m in re.finditer(pat, block, re.IGNORECASE):
                degrees_found.append((m.start(), m.end(), m.group(0)))
                
        # Sort by start pos
        degrees_found.sort(key=lambda x: x[0])
        if not degrees_found:
            continue
            
        for idx, (d_start, d_end, deg_text) in enumerate(degrees_found):
            prev_bound = degrees_found[idx - 1][1] if idx > 0 else 0
            next_bound = degrees_found[idx + 1][0] if idx + 1 < len(degrees_found) else len(block)
            window = block[prev_bound:next_bound]
            
            # 1. Institution / University
            uni = None
            for line in window.split("\n"):
                line_c = line.strip()
                m_uni = re.search(r"\b([A-Z][a-zA-Z0-9\s&.,\'-]*(?:University|Institute(?: of Technology)?|College|Academy|School)[a-zA-Z\s]*)\b", line_c)
                if m_uni:
                    uni = m_uni.group(0).strip(" ,|:-")
                    break
                    
            # 2. Specialization
            spec = None
            m_spec = re.search(re.escape(deg_text) + r"\s+(?:in|of)\s+([A-Za-z\s&]+?)(?:\s*[|,\-\n]|\s+CGPA|\s+GPA|\Z)", window, re.IGNORECASE)
            if m_spec:
                cand = m_spec.group(1).strip()
                if len(cand) < 60:
                    spec = cand
            if not spec:
                for major in COMMON_MAJORS:
                    if re.search(rf"\b{re.escape(major)}\b", window, re.IGNORECASE):
                        spec = major
                        break
                        
            # 3. CGPA / Academic performance
            perf = None
            m_perf = re.search(r"(?:CGPA|GPA|Percentage|Score|Grade)\s*[:=-]?\s*(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?%?)", window, re.IGNORECASE)
            if m_perf:
                perf = m_perf.group(0).strip()
                
            # 4. Years (start_year, end_year, graduation_year)
            start_yr = None
            end_yr = None
            grad_yr = None
            m_years = re.search(r"\b(19\d{2}|20\d{2})\s*[-–—to\s\W]{1,5}\s*(19\d{2}|20\d{2}|Present|Current|Ongoing)\b", window, re.IGNORECASE)
            if m_years:
                start_yr = m_years.group(1)
                end_yr = m_years.group(2)
                grad_yr = end_yr if end_yr not in ["Present", "Current", "Ongoing"] else None
            else:
                m_single = re.search(r"\b(19\d{2}|20\d{2})\b", window)
                if m_single:
                    grad_yr = m_single.group(0)
                    end_yr = grad_yr
                    
            item = EducationItem(
                degree=deg_text.strip(),
                specialization=spec,
                university=uni,
                graduation_year=grad_yr,
                start_year=start_yr,
                end_year=end_yr,
                academic_performance=perf
            )
            
            # Avoid duplicate degrees
            if not any(e.degree == item.degree and e.university == item.university for e in education_entries):
                education_entries.append(item)
                
    return education_entries


def extract_experience(text: str) -> List[ExperienceItem]:
    """Extract professional experience entries."""
    experience_entries: List[ExperienceItem] = []
    
    exp_headers = [
        r"WORK\s+EXPERIENCE", r"PROFESSIONAL\s+EXPERIENCE", r"EMPLOYMENT\s+HISTORY",
        r"EXPERIENCE"
    ]
    section_stoppers = [
        r"PROJECTS?", r"ACADEMIC\s+PROJECTS?", r"PERSONAL\s+PROJECTS?",
        r"EDUCATION", r"ACADEMIC\s+DETAILS",
        r"TECHNICAL\s+SKILLS?", r"SKILLS?", r"CERTIFICATIONS?", r"CERTIFICATES?",
        r"ACHIEVEMENTS?", r"AWARDS?", r"PUBLICATIONS?", r"INTERNSHIPS?",
        r"SUMMARY", r"PROFESSIONAL\s+SUMMARY", r"OBJECTIVE", r"LANGUAGES?"
    ]
    header_rx = r"(?:^|\n)(?:" + "|".join(exp_headers) + r")(?:\s*[:\n])"
    stopper_rx = r"\n(?=(?:" + "|".join(section_stoppers) + r")\b|\Z)"
    
    sec_match = re.search(header_rx + r"(.*?)" + stopper_rx, text, re.IGNORECASE | re.DOTALL)
    if not sec_match:
        return []
    
    exp_block = sec_match.group(1).strip()
    paragraphs = [p.strip() for p in exp_block.split("\n\n") if p.strip()]
    
    common_titles = [
        "Senior Software Engineer", "Senior Backend Developer", "Senior Frontend Developer",
        "Senior Full Stack Developer", "Software Engineer", "Software Developer",
        "Full Stack Developer", "Backend Developer", "Frontend Developer",
        "Data Scientist", "Machine Learning Engineer", "DevOps Engineer",
        "System Architect", "Cloud Architect", "Intern", "Research Assistant",
        "Product Manager", "Data Analyst", "AI Engineer"
    ]
    # Sort by length descending to match more specific titles first
    common_titles.sort(key=len, reverse=True)
    
    for block in paragraphs:
        lines = block.split("\n")
        title_found = None
        for title in common_titles:
            if re.search(rf"\b{re.escape(title)}\b", block, re.IGNORECASE):
                title_found = title
                break
        
        # Look for duration (e.g., "Jan 2022 - Present", "2020 - 2023", "06/2021 - 08/2022")
        duration_match = re.search(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|[0-9]{1,2}/)?\s*[0-9]{4}\s*[-–—to]+\s*(?:Present|[A-Za-z]+\s*[0-9]{4}|[0-9]{4}))", block, re.IGNORECASE)
        duration = duration_match.group(0).strip() if duration_match else None
        
        # Company heuristic: line before or after title
        company = None
        for line in lines[:3]:
            line_c = line.strip()
            if title_found and line_c.lower() == title_found.lower():
                continue
            if duration and duration in line_c:
                continue
            if len(line_c) > 2 and len(line_c) < 60:
                company = line_c
                break
        
        if title_found or company:
            experience_entries.append(ExperienceItem(
                company=company,
                job_title=title_found,
                duration=duration,
                responsibilities=block
            ))
            
    return experience_entries


def extract_projects(text: str) -> List[ProjectItem]:
    """Extract project entries supporting multi-project sections, piped headers, and varied formats."""
    projects: List[ProjectItem] = []
    
    project_headers = [
        r"PROJECTS?", r"ACADEMIC\s+PROJECTS?", r"PERSONAL\s+PROJECTS?",
        r"TECHNICAL\s+PROJECTS?", r"KEY\s+PROJECTS?"
    ]
    section_stoppers = [
        r"EXPERIENCE", r"WORK\s+EXPERIENCE", r"PROFESSIONAL\s+EXPERIENCE",
        r"EMPLOYMENT\s+HISTORY", r"EDUCATION", r"ACADEMIC\s+DETAILS",
        r"TECHNICAL\s+SKILLS?", r"SKILLS?", r"CERTIFICATIONS?", r"CERTIFICATES?",
        r"ACHIEVEMENTS?", r"AWARDS?", r"PUBLICATIONS?", r"INTERNSHIPS?",
        r"SUMMARY", r"PROFESSIONAL\s+SUMMARY", r"OBJECTIVE", r"LANGUAGES?"
    ]
    
    header_rx = r"(?:^|\n)(?:" + "|".join(project_headers) + r")(?:\s*[:\n])"
    stopper_rx = r"\n(?=(?:" + "|".join(section_stoppers) + r")\b|\Z)"
    
    sec_match = re.search(header_rx + r"(.*?)" + stopper_rx, text, re.IGNORECASE | re.DOTALL)
    if not sec_match:
        return []
    
    block = sec_match.group(1).strip()
    lines = block.split("\n")
    bullet_chars = {"•", "-", "*", "–", "—", "\u2022", "\ufffd"}
    
    project_starts = []
    for i, line in enumerate(lines):
        line_s = line.strip()
        if not line_s:
            continue
        if line_s[0] in bullet_chars:
            continue
        if re.match(r"^(?:19\d{2}|20\d{2})(?:\s*[-–—to]+\s*(?:19\d{2}|20\d{2}|Present))?$", line_s, re.I):
            continue
        if line_s.endswith((".", ",", ";")):
            continue
        if line_s[0].islower():
            continue
        if re.match(r"^(?:benchmarked|integrating|added|tested|architected|developed|implemented|designed|built|cut|used)\b", line_s, re.I):
            continue

        if "|" in line_s and len(line_s) < 120:
            project_starts.append(i)
        elif len(line_s.split()) <= 8 and len(line_s) < 70:
            if i + 1 < len(lines):
                next_s = lines[i + 1].strip()
                if re.match(r"^\b(19\d{2}|20\d{2})\b", next_s) or (next_s and next_s[0] in bullet_chars):
                    project_starts.append(i)
                    
    # If explicit project headers were found, segment by those headers
    if project_starts:
        for idx, p_start in enumerate(project_starts):
            p_end = project_starts[idx + 1] if idx + 1 < len(project_starts) else len(lines)
            p_lines = lines[p_start:p_end]
            first_line = p_lines[0].strip()
            
            title = first_line
            tech_list = []
            
            if "|" in first_line:
                parts = first_line.split("|", 1)
                raw_title = parts[0].strip(" -:•*|")
                title = re.sub(r"\s+[a-zA-Z]$", "", raw_title).strip()
                tech_part = parts[1].strip()
                tech_list = [t.strip() for t in re.split(r"[,;/]", tech_part) if t.strip()]
            else:
                title = re.sub(r"\s+[a-zA-Z]$", "", first_line).strip(" -:•*|")
                
            desc = "\n".join(p_lines)
            tech_match = re.search(r"(?:Technologies|Tech Stack|Tools)?\s*[:|]\s*(.*)", desc, re.I)
            if tech_match and not tech_list:
                tech_list = [t.strip() for t in re.split(r"[,;/]", tech_match.group(1)) if t.strip()]
                
            projects.append(ProjectItem(
                name=title,
                description=desc,
                technologies=tech_list
            ))
    else:
        # Fallback to paragraph-based separation (double newline)
        items = [p.strip() for p in block.split("\n\n") if p.strip()]
        for item_text in items:
            item_lines = item_text.split("\n")
            if not item_lines:
                continue
            name = item_lines[0].strip(" -:•*|")
            tech_used = []
            tech_match = re.search(r"(?:Technologies|Tech Stack|Tools)?\s*[:|]\s*(.*)", item_text, re.IGNORECASE)
            if tech_match:
                raw_tech = tech_match.group(1)
                tech_used = [t.strip() for t in re.split(r"[,;|/]", raw_tech) if t.strip()]
            
            projects.append(ProjectItem(
                name=name,
                description=item_text,
                technologies=tech_used
            ))
            
    return projects


def extract_internships(text: str) -> List[InternshipItem]:
    """Extract internship experiences."""
    internships: List[InternshipItem] = []
    sec_match = re.search(r"(?:^|\n)(?:INTERNSHIPS|INTERNSHIP EXPERIENCE)(?:\s*[:\n])(.*?)(?=\n[A-Z\s]{4,}|\Z)", text, re.IGNORECASE | re.DOTALL)
    if not sec_match:
        return []
    
    block = sec_match.group(1).strip()
    items = [p.strip() for p in block.split("\n\n") if p.strip()]
    for item in items:
        lines = item.split("\n")
        role = lines[0].strip() if lines else None
        duration_match = re.search(r"([0-9]{4}\s*[-–—to]+\s*[0-9]{4}|[A-Za-z]+\s*[0-9]{4}\s*[-–—to]+\s*[A-Za-z]+\s*[0-9]{4})", item)
        duration = duration_match.group(0).strip() if duration_match else None
        internships.append(InternshipItem(
            company=None,
            role=role,
            duration=duration,
            responsibilities=item
        ))
    return internships


def extract_certifications(text: str) -> List[CertificationItem]:
    """Extract certifications."""
    certs: List[CertificationItem] = []
    sec_match = re.search(r"(?:^|\n)(?:CERTIFICATIONS|CERTIFICATES|LICENSES)(?:\s*[:\n])(.*?)(?=\n[A-Z\s]{4,}|\Z)", text, re.IGNORECASE | re.DOTALL)
    if not sec_match:
        return []
    
    block = sec_match.group(1).strip()
    lines = [line.strip(" -:•*|") for line in block.split("\n") if line.strip()]
    
    known_issuers = ["AWS", "Google", "Microsoft", "Coursera", "Udacity", "Cisco", "IBM", "Oracle", "Meta"]
    
    for line in lines:
        issuer = None
        for k in known_issuers:
            if re.search(rf"\b{k}\b", line, re.IGNORECASE):
                issuer = k
                break
        year_match = re.search(r"\b(20\d{2}|19\d{2})\b", line)
        year = year_match.group(0) if year_match else None
        certs.append(CertificationItem(
            name=line,
            issuer=issuer,
            year=year
        ))
    return certs


def extract_achievements(text: str) -> List[str]:
    """Extract awards, honors, achievements."""
    sec_match = re.search(r"(?:^|\n)(?:ACHIEVEMENTS|HONORS|AWARDS|ACCOMPLISHMENTS)(?:\s*[:\n])(.*?)(?=\n[A-Z\s]{4,}|\Z)", text, re.IGNORECASE | re.DOTALL)
    if not sec_match:
        return []
    block = sec_match.group(1).strip()
    lines = [l.strip(" -:•*|") for l in block.split("\n") if l.strip()]
    return lines

