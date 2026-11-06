import io
import re
from typing import Tuple
import fitz  # PyMuPDF
import docx

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # often sent by generic clients for docx/pdf
}

class ResumeParserError(Exception):
    """Custom exception raised when resume parsing fails."""
    pass

class UnsupportedFormatError(ResumeParserError):
    pass

class CorruptedFileError(ResumeParserError):
    pass

class EmptyFileError(ResumeParserError):
    pass

class ScannedPdfError(ResumeParserError):
    pass

class FileSizeExceededError(ResumeParserError):
    pass


def clean_text(raw_text: str) -> str:
    """Normalize whitespace and preserve paragraph/section structure."""
    if not raw_text:
        return ""
    # Replace non-breaking spaces and special unicode spaces
    text = raw_text.replace("\xa0", " ").replace("\u200b", "")
    # Normalize carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Replace horizontal runs of tabs/spaces with single space
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3 or more newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def validate_file_metadata(filename: str, content_type: str, file_size: int) -> None:
    """Validate file extension, size, and MIME type."""
    if file_size > MAX_FILE_SIZE:
        raise FileSizeExceededError(
            f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB (got {file_size / (1024 * 1024):.2f}MB)"
        )
    
    # Check extension
    dot_idx = filename.rfind(".")
    if dot_idx == -1:
        raise UnsupportedFormatError(f"File '{filename}' has no extension. Only .pdf and .docx are supported.")
    ext = filename[dot_idx:].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(f"Unsupported file extension '{ext}'. Only .pdf and .docx are supported.")


ICON_FONTS = {
    "fontawesome", "font-awesome", "glyphicon", "materialicon",
    "icomoon", "feather", "typicons", "ionicons"
}


def parse_pdf(file_bytes: bytes) -> str:
    """Extract structured text from PDF bytes using PyMuPDF (fitz), filtering out icon font artifacts."""
    if len(file_bytes) == 0:
        raise EmptyFileError("Uploaded PDF file is completely empty (0 bytes).")
    
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise CorruptedFileError(f"Failed to open PDF document (corrupted or invalid format): {str(e)}")
    
    try:
        if len(doc) == 0:
            raise EmptyFileError("PDF document has 0 pages.")
        
        extracted_pages = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_lines = []
            
            # Extract structured blocks and spans to identify icon fonts
            blocks = page.get_text("dict").get("blocks", [])
            for b in blocks:
                if "lines" in b:
                    for line in b["lines"]:
                        line_spans = []
                        for s in line.get("spans", []):
                            font_lower = s.get("font", "").lower()
                            # Check if span belongs to an icon font and is an icon glyph
                            if any(ik in font_lower for ik in ICON_FONTS) and len(s.get("text", "").strip()) <= 2:
                                continue
                            line_spans.append(s.get("text", ""))
                        line_str = "".join(line_spans).strip()
                        if line_str:
                            page_lines.append(line_str)
                            
            if page_lines:
                extracted_pages.append("\n".join(page_lines))
            else:
                raw = page.get_text("text").strip()
                if raw:
                    extracted_pages.append(raw)
        
        full_text = "\n\n".join(extracted_pages)
        cleaned = clean_text(full_text)
        
        if len(cleaned.strip()) == 0:
            raise ScannedPdfError(
                "PDF contains pages but no extractable text was found. "
                "The document may be scanned or image-only."
            )
        
        return cleaned
    finally:
        doc.close()


def parse_docx(file_bytes: bytes) -> str:
    """Extract structured text from DOCX bytes using python-docx."""
    if len(file_bytes) == 0:
        raise EmptyFileError("Uploaded DOCX file is completely empty (0 bytes).")
    
    try:
        doc_stream = io.BytesIO(file_bytes)
        doc = docx.Document(doc_stream)
    except Exception as e:
        raise CorruptedFileError(f"Failed to read DOCX document (corrupted or invalid format): {str(e)}")
    
    paragraphs = []
    # Extract from main paragraphs
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            paragraphs.append(txt)
    
    # Extract from tables (resumes often put experience/skills in tables)
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                paragraphs.append(" | ".join(row_texts))
    
    full_text = "\n".join(paragraphs)
    cleaned = clean_text(full_text)
    
    if len(cleaned.strip()) == 0:
        raise EmptyFileError("DOCX document contains no text content.")
    
    return cleaned


def parse_resume_bytes(file_bytes: bytes, filename: str, content_type: str = "") -> str:
    """Top-level parser: validates metadata and dispatches to appropriate parser.
    
    Parameters
    ----------
    file_bytes : bytes
        Raw file content in memory.
    filename : str
        Original filename.
    content_type : str
        MIME type provided by client.
        
    Returns
    -------
    str
        Cleaned, extracted text from the resume.
    """
    validate_file_metadata(filename, content_type, len(file_bytes))
    
    ext = filename[filename.rfind("."):].lower()
    if ext == ".pdf":
        return parse_pdf(file_bytes)
    elif ext == ".docx":
        return parse_docx(file_bytes)
    else:
        raise UnsupportedFormatError(f"Unsupported file extension '{ext}'. Only .pdf and .docx are supported.")

