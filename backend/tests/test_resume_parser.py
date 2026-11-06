import io
import pytest
import fitz
import docx
from resume.parser import (
    parse_resume_bytes,
    parse_pdf,
    parse_docx,
    UnsupportedFormatError,
    CorruptedFileError,
    EmptyFileError,
    ScannedPdfError,
    FileSizeExceededError,
)

def create_sample_pdf(text: str, num_pages: int = 1) -> bytes:
    """Helper to generate a real in-memory PDF."""
    doc = fitz.open()
    for _ in range(num_pages):
        page = doc.new_page()
        # insert text into the page
        page.insert_text((50, 50), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

def create_sample_docx(paragraphs: list[str]) -> bytes:
    """Helper to generate a real in-memory DOCX."""
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def test_parse_valid_pdf():
    resume_text = "John Doe\nSoftware Engineer\nPython, Docker, SQL\nB.Tech Computer Science"
    pdf_bytes = create_sample_pdf(resume_text)
    result = parse_resume_bytes(pdf_bytes, "john_doe.pdf", "application/pdf")
    assert "John Doe" in result
    assert "Software Engineer" in result
    assert "Python" in result

def test_parse_valid_docx():
    paragraphs = [
        "Jane Smith",
        "Senior Backend Developer",
        "Python, FastAPI, PostgreSQL, Kubernetes",
        "Education: M.S. in Computer Science"
    ]
    docx_bytes = create_sample_docx(paragraphs)
    result = parse_resume_bytes(docx_bytes, "jane_smith.docx")
    assert "Jane Smith" in result
    assert "FastAPI" in result
    assert "PostgreSQL" in result

def test_parse_multipage_pdf():
    page1 = "Alice Wonderland\nPage 1 - Experience: Tech Lead at Acme Corp"
    page2 = "Page 2 - Education: Ph.D. in Computer Science from MIT"
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), page1)
    p2 = doc.new_page()
    p2.insert_text((50, 50), page2)
    pdf_bytes = doc.write()
    doc.close()
    
    result = parse_resume_bytes(pdf_bytes, "alice.pdf")
    assert "Page 1" in result
    assert "Page 2" in result
    assert "Acme Corp" in result
    assert "Ph.D." in result

def test_empty_pdf_bytes():
    with pytest.raises(EmptyFileError):
        parse_resume_bytes(b"", "empty.pdf")

def test_corrupted_pdf():
    corrupted_bytes = b"%PDF-1.4 Not A Valid PDF Stream Content..."
    with pytest.raises(CorruptedFileError):
        parse_resume_bytes(corrupted_bytes, "corrupt.pdf")

def test_scanned_pdf():
    # PDF with pages but no text
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.write()
    doc.close()
    with pytest.raises(ScannedPdfError):
        parse_resume_bytes(pdf_bytes, "scanned.pdf")

def test_unsupported_format():
    with pytest.raises(UnsupportedFormatError):
        parse_resume_bytes(b"hello world", "resume.txt")

def test_file_size_exceeded():
    huge_bytes = b"0" * (6 * 1024 * 1024)
    with pytest.raises(FileSizeExceededError):
        parse_resume_bytes(huge_bytes, "large.pdf")

