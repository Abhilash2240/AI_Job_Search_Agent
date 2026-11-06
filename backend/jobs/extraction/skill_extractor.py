"""
Job Skill Extractor (Phase 4C).
Extracts required and preferred skills with categorized taxonomy and original evidence snippets.
Distinguishes required skills from preferred/nice-to-have skills.
"""

import re
from typing import Dict, List, Set, Tuple
from jobs.job_schema import SkillWithEvidence


JOB_SKILL_TAXONOMY: Dict[str, Dict[str, str]] = {
    "Programming Languages": {
        "python": "Python",
        "java": "Java",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "golang": "Go",
        "go": "Go",
        "c++": "C++",
        "c#": "C#",
        "ruby": "Ruby",
        "rust": "Rust",
        "php": "PHP",
        "scala": "Scala",
        "kotlin": "Kotlin",
        "swift": "Swift",
        "sql": "SQL",
        "bash": "Bash",
        "shell": "Shell",
    },
    "Frameworks": {
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "react": "React",
        "react.js": "React",
        "node.js": "Node.js",
        "nodejs": "Node.js",
        "express": "Express.js",
        "express.js": "Express.js",
        "spring boot": "Spring Boot",
        "spring": "Spring",
        "vue": "Vue.js",
        "angular": "Angular",
        "next.js": "Next.js",
        "nest.js": "NestJS",
        "graphql": "GraphQL",
        "rest api": "REST APIs",
        "rest apis": "REST APIs",
        "restful apis": "REST APIs",
        "grpc": "gRPC",
    },
    "Databases": {
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mysql": "MySQL",
        "mongodb": "MongoDB",
        "redis": "Redis",
        "cassandra": "Cassandra",
        "sqlite": "SQLite",
        "dynamodb": "DynamoDB",
        "elasticsearch": "Elasticsearch",
        "neo4j": "Neo4j",
    },
    "Cloud Platforms": {
        "aws": "AWS",
        "amazon web services": "AWS",
        "azure": "Azure",
        "gcp": "Google Cloud Platform",
        "google cloud": "Google Cloud Platform",
        "cloudflare": "Cloudflare",
        "heroku": "Heroku",
    },
    "AI/ML": {
        "pytorch": "PyTorch",
        "tensorflow": "TensorFlow",
        "scikit-learn": "Scikit-Learn",
        "langchain": "LangChain",
        "llm": "LLMs",
        "llms": "LLMs",
        "rag": "RAG",
        "embeddings": "Embeddings",
        "sbert": "SBERT",
        "nlp": "Natural Language Processing",
        "computer vision": "Computer Vision",
        "machine learning": "Machine Learning",
        "deep learning": "Deep Learning",
    },
    "Data Engineering": {
        "spark": "Apache Spark",
        "apache spark": "Apache Spark",
        "kafka": "Apache Kafka",
        "apache kafka": "Apache Kafka",
        "airflow": "Apache Airflow",
        "hadoop": "Hadoop",
        "snowflake": "Snowflake",
        "databricks": "Databricks",
        "etl": "ETL",
        "data pipelines": "Data Pipelines",
    },
    "DevOps": {
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "k8s": "Kubernetes",
        "ci/cd": "CI/CD",
        "terraform": "Terraform",
        "ansible": "Ansible",
        "linux": "Linux",
        "github actions": "GitHub Actions",
        "helm": "Helm",
    },
    "Testing": {
        "pytest": "PyTest",
        "unit testing": "Unit Testing",
        "integration testing": "Integration Testing",
        "jest": "Jest",
        "selenium": "Selenium",
        "cypress": "Cypress",
        "tdd": "TDD",
        "automated testing": "Automated Testing",
    },
    "Tools": {
        "git": "Git",
        "github": "GitHub",
        "jira": "JIRA",
        "postman": "Postman",
    },
    "Soft Skills": {
        "problem solving": "Problem Solving",
        "communication": "Communication",
        "teamwork": "Teamwork",
        "collaboration": "Collaboration",
        "leadership": "Leadership",
        "critical thinking": "Critical Thinking",
    },
}


class SkillExtractor:
    """Extracts required and preferred skills with category metadata and context snippets."""

    @classmethod
    def extract_skills_from_text(
        cls, text: str, is_required: bool = True
    ) -> List[SkillWithEvidence]:
        """Scans a text block for skills in the taxonomy and captures snippet evidence."""
        if not text:
            return []

        results: List[SkillWithEvidence] = []
        seen_canonical: Set[str] = set()

        # Split into sentence or bullet-like lines
        lines = [line.strip() for line in re.split(r"[\n•\.;]", text) if line.strip()]

        for category, skill_map in JOB_SKILL_TAXONOMY.items():
            for alias, canonical in skill_map.items():
                if canonical.lower() in seen_canonical:
                    continue

                # Word boundary pattern
                escaped = re.escape(alias)
                pattern = rf"(?:^|[\s,;|/()\[\]]){escaped}(?:$|[\s,;|/()\[\]])"

                for line in lines:
                    if re.search(pattern, line, re.IGNORECASE):
                        snippet = line[:180].strip()
                        results.append(
                            SkillWithEvidence(
                                skill_name=alias.title(),
                                canonical_name=canonical,
                                category=category,
                                evidence_snippet=snippet,
                                is_required=is_required,
                            )
                        )
                        seen_canonical.add(canonical.lower())
                        break

        return results

    @classmethod
    def extract_from_segmented_job(
        cls,
        summary: str,
        responsibilities: List[str],
        qualifications: List[str],
        preferred_qualifications: List[str],
        full_text: str,
    ) -> Tuple[List[SkillWithEvidence], List[SkillWithEvidence]]:
        """
        Extracts required skills from requirements & duties, and preferred skills from nice-to-haves.
        """
        # 1. Preferred skills from preferred section
        pref_text = "\n".join(preferred_qualifications)
        preferred_skills = cls.extract_skills_from_text(pref_text, is_required=False)
        preferred_canonicals = {s.canonical_name.lower() for s in preferred_skills}

        # 2. Required skills from qualifications, responsibilities, and summary
        req_text = f"{summary}\n" + "\n".join(qualifications) + "\n" + "\n".join(responsibilities)
        if not req_text.strip():
            req_text = full_text

        raw_req_skills = cls.extract_skills_from_text(req_text, is_required=True)
        required_skills: List[SkillWithEvidence] = []

        for skill in raw_req_skills:
            if skill.canonical_name.lower() not in preferred_canonicals:
                required_skills.append(skill)

        return required_skills, preferred_skills

