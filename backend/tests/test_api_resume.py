import io
import pytest
from fastapi.testclient import TestClient
import fitz
import docx

from app.main import app
from db import database

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def create_test_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    data = doc.write()
    doc.close()
    return data

def create_test_docx_bytes(paragraphs: list[str]) -> bytes:
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

SAMPLE_RESUME_TEXT = """
Devin AI
devin@example.com
(415) 888-9999
San Jose, CA

EDUCATION
B.Tech in Computer Science
San Jose State University
2021
GPA: 3.8

SKILLS
Python, FastAPI, Docker, AWS, PostgreSQL, React, Git

EXPERIENCE
Software Engineer at CloudTech
2021 - Present
Developing high-throughput microservices.

PROJECTS
Job Search Assistant
AI-powered job search engine.
"""

def test_api_upload_pdf(client):
    pdf_bytes = create_test_pdf_bytes(SAMPLE_RESUME_TEXT)
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "candidate_id" in data
    assert data["filename"] == "resume.pdf"
    assert data["validation"]["status"] == "VALID"
    assert "Python" in data["profile"]["skills"]["programming_languages"]
    assert data["profile"]["personal"]["name"] == "Devin AI"
    
    # Test retrieving candidate profile
    candidate_id = data["candidate_id"]
    get_res = client.get(f"/api/resume/{candidate_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["candidate_id"] == candidate_id
    assert retrieved["profile"]["personal"]["name"] == "Devin AI"

    # Cleanup test fixture candidate to maintain database isolation
    import sqlite3
    from db.database import DEFAULT_DB_FILE
    with sqlite3.connect(DEFAULT_DB_FILE) as conn:
        conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        conn.commit()

def test_api_upload_docx(client):
    docx_bytes = create_test_docx_bytes(SAMPLE_RESUME_TEXT.split("\n"))
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["validation"]["status"] == "VALID"
    assert "FastAPI" in data["profile"]["skills"]["frameworks"]

    # Cleanup test fixture candidate to maintain database isolation
    candidate_id = data.get("candidate_id")
    if candidate_id:
        import sqlite3
        from db.database import DEFAULT_DB_FILE
        with sqlite3.connect(DEFAULT_DB_FILE) as conn:
            conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
            conn.commit()

def test_api_upload_unsupported(client):
    response = client.post(
        "/api/resume/upload",
        files={"file": ("notes.txt", b"plain text", "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]

def test_api_upload_empty(client):
    response = client.post(
        "/api/resume/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_api_get_nonexistent(client):
    response = client.get("/api/resume/999999")
    assert response.status_code == 404
