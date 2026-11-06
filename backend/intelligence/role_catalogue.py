from typing import List
from schemas.role import CareerRole

DEFAULT_ROLE_CATALOGUE: List[CareerRole] = [
    CareerRole(
        role_id="software_engineer",
        title="Software Engineer",
        description=(
            "Designs, develops, tests, and delivers modular software solutions. Applies core computer science "
            "principles including data structures, algorithms, object-oriented design, automated testing, and "
            "version control. Open to entry-level software development engineers (SDE-1) and early-career technologists "
            "with strong problem-solving and software engineering fundamentals."
        ),
        required_skills=["Python", "Data Structures", "Algorithms", "Object-Oriented Design", "Git"],
        preferred_skills=["SQL", "Unit Testing", "Automated Testing", "REST APIs", "Docker", "AWS", "Complexity Analysis"],
        alternative_titles_entry=[
            "Associate Software Engineer", "Junior Software Engineer", "Software Development Engineer I (SDE-1)",
            "Graduate Software Developer"
        ],
        alternative_titles_experienced=[
            "Software Development Engineer", "Software Engineer", "Systems Software Engineer"
        ],
        domain_keywords=["software engineering", "algorithms", "data structures", "testing", "clean code", "system design"]
    ),
    CareerRole(
        role_id="python_backend_engineer",
        title="Python Backend Engineer",
        description=(
            "Builds reliable server-side services, data pipelines, and RESTful APIs using Python. Focuses on database schema "
            "modeling, request validation, transaction integrity, automated testing, and cloud infrastructure deployment."
        ),
        required_skills=["Python", "REST APIs", "SQL", "Git"],
        preferred_skills=["FastAPI", "DBMS", "Docker", "AWS", "Automated Testing", "Data Validation", "Data Pipelines"],
        alternative_titles_entry=[
            "Associate Backend Engineer", "Junior Python Backend Developer", "Junior API Developer", "Graduate Backend Developer"
        ],
        alternative_titles_experienced=[
            "Backend Engineer (Python)", "Python Backend Developer", "API Systems Engineer"
        ],
        domain_keywords=["backend", "api", "rest", "server", "fastapi", "django", "flask", "database", "sql"]
    ),
    CareerRole(
        role_id="ai_engineer",
        title="AI Engineer",
        description=(
            "Architects and implements intelligent applications integrating Large Language Models (LLMs), AI agents, "
            "retrieval-augmented generation (RAG), vector embeddings, semantic search, and prompt engineering. "
            "Specializes in multi-module agentic automation and LLM API integrations."
        ),
        required_skills=["Python", "LLMs", "AI Agents"],
        preferred_skills=["Google Gemini API", "RAG", "Semantic Search", "Embeddings", "Object-Oriented Design", "FastAPI", "Docker"],
        alternative_titles_entry=[
            "Associate AI Engineer", "Junior AI Engineer", "AI Application Developer", "Junior Generative AI Developer"
        ],
        alternative_titles_experienced=[
            "Generative AI Engineer", "Applied AI Developer", "AI Systems Engineer"
        ],
        domain_keywords=["ai agents", "llms", "gemini", "rag", "embeddings", "semantic search", "generative ai"]
    ),
    CareerRole(
        role_id="ai_ml_engineer",
        title="AI/ML Engineer",
        description=(
            "Develops, trains, benchmarks, and evaluates machine learning and deep learning models for production applications. "
            "Proficient in supervised learning, model evaluation metrics (F1-score, ROC-AUC, precision/recall), transformers, "
            "and reproducible ML pipelines."
        ),
        required_skills=["Python", "Machine Learning", "Model Evaluation"],
        preferred_skills=["PyTorch", "Supervised Machine Learning", "Google Gemini API", "LLMs", "RAG", "Scikit-Learn", "Embeddings"],
        alternative_titles_entry=[
            "Associate AI/ML Engineer", "Junior Machine Learning Engineer", "Junior Data & ML Developer", "Applied ML Trainee"
        ],
        alternative_titles_experienced=[
            "Applied ML Engineer", "Machine Learning Engineer", "AI/ML Solutions Developer"
        ],
        domain_keywords=["machine learning", "deep learning", "models", "evaluation", "roc-auc", "f1-score", "nlp", "training"]
    ),
    CareerRole(
        role_id="automation_engineer",
        title="Automation Engineer",
        description=(
            "Engineers automated test suites, end-to-end task-routing workflows, data validation pipelines, and CI/CD "
            "verification systems. Guarantees high test coverage, reliability, and automated fault detection."
        ),
        required_skills=["Python", "Automated Testing", "Unit Testing", "Git"],
        preferred_skills=["Quality Engineering", "Reliability Testing", "Data Validation", "AI Agents", "Docker", "CI/CD"],
        alternative_titles_entry=[
            "Associate Automation Engineer", "Junior SDET", "Junior QA Automation Engineer", "Test Automation Developer"
        ],
        alternative_titles_experienced=[
            "SDET", "Software Development Engineer in Test", "Automation QA Engineer"
        ],
        domain_keywords=["automation", "testing", "coverage", "reliability", "qa", "validation", "test suites"]
    ),
    CareerRole(
        role_id="data_engineer",
        title="Data Engineer",
        description=(
            "Constructs data ingestion pipelines, ETL/ELT workflows, relational database schemas, and data-quality frameworks. "
            "Focuses on SQL query optimization, DBMS architecture, and structured data delivery."
        ),
        required_skills=["Python", "SQL", "DBMS", "Data Pipelines"],
        preferred_skills=["Data Validation", "Data Quality", "AWS", "Docker", "Data Structures", "PostgreSQL"],
        alternative_titles_entry=[
            "Associate Data Engineer", "Junior Data Pipeline Developer", "Junior ETL Developer", "Graduate Data Engineer"
        ],
        alternative_titles_experienced=[
            "Data Engineer", "Data Platform Engineer", "ETL Developer"
        ],
        domain_keywords=["data pipeline", "etl", "sql", "dbms", "database", "warehousing", "data quality"]
    ),
    CareerRole(
        role_id="python_developer",
        title="Python Developer",
        description=(
            "Develops clean, modular, and well-tested Python applications, automation scripts, and database integrations. "
            "Demonstrates solid command of Python core libraries, object-oriented programming, and version control."
        ),
        required_skills=["Python", "Git", "Object-Oriented Design"],
        preferred_skills=["SQL", "REST APIs", "Unit Testing", "Docker", "AWS", "FastAPI"],
        alternative_titles_entry=[
            "Junior Python Developer", "Associate Python Programmer", "Graduate Python Engineer"
        ],
        alternative_titles_experienced=[
            "Python Developer", "Python Software Engineer", "Core Python Developer"
        ],
        domain_keywords=["python", "scripting", "oop", "clean code", "git", "standard library"]
    ),
    CareerRole(
        role_id="machine_learning_engineer",
        title="Machine Learning Engineer",
        description=(
            "Builds statistical learning systems, predictive models, data preprocessing pipelines, and model benchmarking suites. "
            "Applies rigorous validation protocols to ensure model accuracy, generalizability, and reliability."
        ),
        required_skills=["Python", "Machine Learning", "Model Evaluation", "SQL"],
        preferred_skills=["Supervised Machine Learning", "Data Validation", "Scikit-Learn", "PyTorch", "Docker"],
        alternative_titles_entry=[
            "Junior ML Engineer", "Associate Machine Learning Developer", "Graduate ML Specialist"
        ],
        alternative_titles_experienced=[
            "Machine Learning Engineer", "Predictive Modeling Engineer", "ML Systems Developer"
        ],
        domain_keywords=["machine learning", "predictive", "statistics", "scikit-learn", "features", "evaluation"]
    ),
    CareerRole(
        role_id="backend_developer",
        title="Backend Developer",
        description=(
            "Develops server-side logic, relational schemas, secure API endpoints, and modular business components. "
            "Emphasizes clean architecture, data consistency, and thorough test verification."
        ),
        required_skills=["Python", "SQL", "REST APIs", "Git"],
        preferred_skills=["DBMS", "Data Validation", "Docker", "AWS", "Object-Oriented Design", "Unit Testing"],
        alternative_titles_entry=[
            "Associate Backend Developer", "Junior Server-Side Developer", "Junior API Engineer"
        ],
        alternative_titles_experienced=[
            "Backend Developer", "Server-Side Software Engineer", "Backend Systems Engineer"
        ],
        domain_keywords=["backend", "server", "api", "database", "architecture", "endpoints"]
    ),
    CareerRole(
        role_id="full_stack_developer",
        title="Full Stack Developer",
        description=(
            "Builds complete web applications combining client-side user interfaces with backend API services. "
            "Coordinates database schemas, REST endpoints, UI interactions, and automated testing."
        ),
        required_skills=["JavaScript", "Python", "REST APIs", "HTML5"],
        preferred_skills=["React", "SQL", "CSS3", "Docker", "Git", "FastAPI"],
        alternative_titles_entry=[
            "Associate Full Stack Developer", "Junior Full Stack Engineer", "Graduate Web Application Developer"
        ],
        alternative_titles_experienced=[
            "Full Stack Developer", "Full Stack Software Engineer", "Web Applications Engineer"
        ],
        domain_keywords=["frontend", "backend", "full stack", "react", "javascript", "web", "html", "css"]
    )
]


def get_role_catalogue() -> List[CareerRole]:
    """Retrieve the configurable career role catalogue."""
    return DEFAULT_ROLE_CATALOGUE
