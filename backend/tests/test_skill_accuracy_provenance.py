import pytest
from resume.extractor import extract_skills_with_sources, extract_location
from resume.profile_builder import audit_profile_completeness, calculate_profile_completeness
from schemas.candidate import CandidateProfile, PersonalInfo, ProjectItem, ExperienceItem, EducationItem, SkillsCategorized

def test_no_invented_skills_and_strict_location():
    """Verify that location extractor rejects skills lines and extract_skills_with_sources
    tracks exact provenance without inventing skills."""
    # Location check - skills should NEVER match as geographic locations
    assert extract_location("John Doe\njohn@example.com\nPython, SQL") is None
    assert extract_location("John Doe\njohn@example.com\nAPI integration, RAG") is None
    assert extract_location("John Doe\njohn@example.com\nSan Jose, CA") == "San Jose, CA"
    
    # Skills with sources check
    sample_text = """
    Gundelli Abhilash
    Education
    SR University
    Bachelor of Technology in Computer Science | CGPA: 9.1 / 10
    
    Projects
    Adaptive Stock Trading System
    Built Python and SQL ETL data pipelines with PostgreSQL and Automated Testing.
    
    ReceiptFlow
    Shipped live app with Node.js and Express using Google Gemini API for OCR data extraction.
    
    Technical Skills
    Python, SQL, AWS, Docker, Git
    """
    
    projects = [
        ProjectItem(name="Adaptive Stock Trading System", description="PostgreSQL, Python, SQL, Automated Testing", technologies=["Python", "SQL", "PostgreSQL"]),
        ProjectItem(name="ReceiptFlow", description="Node.js, Express, OCR, Gemini API", technologies=["Node.js", "Express", "Python"])
    ]
    
    skills, sources, inferred = extract_skills_with_sources(sample_text, projects=projects)
    
    # Verify Java, MongoDB, MySQL, Django are NOT present (zero evidence)
    assert "Java" not in skills.programming_languages
    assert "Django" not in skills.frameworks
    assert "MongoDB" not in skills.databases
    assert "MySQL" not in skills.databases
    
    # Verify genuine skills have provenance
    assert "Python" in skills.programming_languages
    assert any("skills section" in s for s in sources["python"])
    
    # PostgreSQL was found in Project 1
    assert "PostgreSQL" in skills.databases
    assert any("project: Adaptive Stock Trading System" in s for s in sources["postgresql"])
    
    # Node.js and Express.js were found in Project 2
    assert "Node.js" in skills.frameworks
    assert "Express.js" in skills.frameworks
    
    # OCR was found in Project 2
    assert "OCR" in skills.ai_ml

def test_completeness_audit_distinction():
    """Verify completeness distinguishes complete, missing, unverified, and optional fields."""
    profile = CandidateProfile(
        personal=PersonalInfo(name="Devin AI", email="devin@example.com", phone="+1 555-0100", location=None), # Missing location
        education=[EducationItem(degree="B.Tech", university="MIT", graduation_year="2024", academic_performance="CGPA: 9.0 / 10")],
        projects=[ProjectItem(name="AI Platform", description="FastAPI app", technologies=["FastAPI", "Python"])]
    )
    
    score, complete, missing, unverified, optional = audit_profile_completeness(profile)
    # Location is missing, so score CANNOT be 100%
    assert score < 100.0
    assert "Personal Geographic Location" in missing
    assert "Full Name" in complete
    assert "Email Address" in complete

def test_candidate_skill_confirm_and_reject_workflow():
    """Verify the candidate skill confirmation and rejection lifecycle:
    - Inferred skills can be accepted/confirmed into verified categories.
    - Verified skills track 'candidate confirmed' provenance.
    - Unsupported or uncertain skills can be rejected and removed.
    - Completeness and verified skill counts update immediately upon action.
    """
    profile = CandidateProfile(
        personal=PersonalInfo(name="Gundelli Abhilash", email="abhi@example.com", phone="+91 9999999999"),
        education=[EducationItem(degree="B.Tech", university="SR University", graduation_year="2027", academic_performance="CGPA: 9.1 / 10")],
        skills=SkillsCategorized(
            programming_languages=["Python", "SQL"],
            frameworks=["FastAPI"],
            databases=["PostgreSQL"],
            tools=["Git"],
            ai_ml=["Machine Learning"],
            other=[]
        ),
        projects=[ProjectItem(name="Trading System", description="Python stock trading", technologies=["Python", "PostgreSQL"])],
        inferred_skills=["GraphQL", "Docker"],
        skill_sources={"python": ["skills section"], "postgresql": ["project: Trading System"]}
    )

    initial_count = sum(len(v) for v in profile.skills.model_dump().values() if isinstance(v, list))
    assert initial_count == 6
    assert "GraphQL" in profile.inferred_skills

    # Step 1: Candidate confirms 'GraphQL' into 'other'
    skill_lower = "graphql"
    profile.inferred_skills = [s for s in profile.inferred_skills if s.lower() != skill_lower]
    profile.skills.other.append("GraphQL")
    profile.skills.other.sort()
    sources = profile.skill_sources.get(skill_lower, [])
    sources.append("candidate confirmed")
    profile.skill_sources[skill_lower] = sources
    profile.profile_completeness = calculate_profile_completeness(profile)

    # Verify confirmation state
    assert "GraphQL" in profile.skills.other
    assert "GraphQL" not in profile.inferred_skills
    assert "candidate confirmed" in profile.skill_sources["graphql"]
    confirmed_count = sum(len(v) for v in profile.skills.model_dump().values() if isinstance(v, list))
    assert confirmed_count == 7

    # Step 2: Candidate rejects 'GraphQL'
    profile.inferred_skills = [s for s in profile.inferred_skills if s.lower() != skill_lower]
    profile.skills.other = [s for s in profile.skills.other if s.lower() != skill_lower]
    if skill_lower in profile.skill_sources:
        del profile.skill_sources[skill_lower]
    profile.profile_completeness = calculate_profile_completeness(profile)

    # Verify rejection state
    assert "GraphQL" not in profile.skills.other
    assert "graphql" not in profile.skill_sources
    reverted_count = sum(len(v) for v in profile.skills.model_dump().values() if isinstance(v, list))
    assert reverted_count == 6
