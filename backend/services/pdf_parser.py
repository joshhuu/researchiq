"""
pdf_parser.py
Extracts raw text and detects paper sections from a PDF file.
"""
import re
import pdfplumber
from typing import Dict, Tuple


SECTION_KEYWORDS = {
    "abstract": ["abstract"],
    "introduction": ["introduction", "1. introduction", "1 introduction"],
    "related_work": ["related work", "literature review", "background"],
    "methodology": ["methodology", "methods", "proposed method", "approach", "3. method"],
    "results": ["results", "experiments", "evaluation", "findings"],
    "discussion": ["discussion", "analysis"],
    "conclusion": ["conclusion", "conclusions", "concluding remarks"],
    "references": ["references", "bibliography"],
}


def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
    """Return (full_text, page_count) from a PDF file."""
    full_text = []
    page_count = 0
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
    return "\n".join(full_text), page_count


def detect_sections(raw_text: str) -> Dict[str, str]:
    """
    Split the raw text into named sections.
    Returns a dict like {"abstract": "...", "methodology": "...", ...}
    Falls back to returning the full text under "full_text" if no sections found.
    """
    lines = raw_text.split("\n")
    sections: Dict[str, list] = {}
    current_section = "preamble"
    sections[current_section] = []

    for line in lines:
        stripped = line.strip().lower()
        matched = False
        for section_name, keywords in SECTION_KEYWORDS.items():
            for kw in keywords:
                if stripped == kw or stripped.startswith(kw + " ") or stripped == kw + ":":
                    current_section = section_name
                    sections.setdefault(current_section, [])
                    matched = True
                    break
            if matched:
                break
        if not matched:
            sections.setdefault(current_section, []).append(line)

    # Convert lists to strings, drop empty sections
    result = {}
    for k, v in sections.items():
        text = "\n".join(v).strip()
        if text:
            result[k] = text

    # If nothing was detected beyond preamble, just use the full text
    if set(result.keys()) <= {"preamble"}:
        result = {"full_text": raw_text}

    return result


def infer_title(raw_text: str) -> str:
    """Heuristically infer paper title from the first non-empty line."""
    for line in raw_text.split("\n"):
        line = line.strip()
        if len(line) > 10 and len(line) < 200:
            return line
    return "Untitled Paper"


import json

async def parse_pdf(file_path: str) -> dict:
    """
    Full pipeline: extract text, detect sections, infer title.
    Returns dict with keys: title, extracted_text, sections (JSON string), page_count.
    """
    raw_text, page_count = extract_text_from_pdf(file_path)
    sections = detect_sections(raw_text)
    title = infer_title(raw_text)
    return {
        "title": title,
        "extracted_text": raw_text,
        "sections": json.dumps(sections),
        "page_count": page_count,
    }
