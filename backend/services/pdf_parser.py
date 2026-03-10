"""
pdf_parser.py
Extracts raw text from PDFs and identifies paper sections.

Extraction strategy:
  1. PyMuPDF (fitz) — faster, handles complex layouts and embedded fonts well
  2. pdfplumber     — fallback for PDFs where PyMuPDF extracts garbled text

Section detection uses a two-pass approach:
  1. Exact header matching against a curated keyword table
  2. Regex pattern matching for numbered section headings (e.g. "1. Introduction")
"""
import re
import json
from typing import Dict, Tuple, Optional

# ── Extraction backends ───────────────────────────────────────────────────────
try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
except ImportError:
    _HAS_FITZ = False

try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False


# ── Section keyword registry ──────────────────────────────────────────────────
# Maps canonical section name → list of header strings to match (lowercased)
SECTION_KEYWORDS: Dict[str, list] = {
    "abstract": [
        "abstract",
    ],
    "introduction": [
        "introduction", "1. introduction", "1 introduction",
        "i. introduction", "background", "overview",
    ],
    "related_work": [
        "related work", "related works", "literature review",
        "prior work", "previous work", "background and related work",
        "2. related work",
    ],
    "methodology": [
        "methodology", "method", "methods", "proposed method",
        "approach", "our approach", "system design",
        "model", "proposed model", "3. methodology", "3. method",
        "materials and methods",
    ],
    "results": [
        "results", "experimental results", "experiments",
        "evaluation", "findings", "performance",
        "4. results", "4. experiments", "5. results",
    ],
    "discussion": [
        "discussion", "analysis", "ablation study",
        "5. discussion", "6. discussion",
    ],
    "conclusion": [
        "conclusion", "conclusions", "concluding remarks",
        "conclusion and future work", "summary and conclusion",
        "6. conclusion", "7. conclusion",
    ],
    "references": [
        "references", "bibliography", "works cited",
    ],
}

# Regex for numbered section headers like "1.", "2.1", "IV."
_NUMBERED_SECTION_RE = re.compile(
    r"^(\d{1,2}\.?\d{0,2}\.?|[IVXivx]{1,5}\.)\s+(.+)$"
)


# ── Text extraction ───────────────────────────────────────────────────────────
def _extract_with_fitz(file_path: str) -> Tuple[str, int]:
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        txt = page.get_text("text")
        if txt:
            pages.append(txt)
    doc.close()
    return "\n".join(pages), len(pages)


def _extract_with_pdfplumber(file_path: str) -> Tuple[str, int]:
    pages = []
    with pdfplumber.open(file_path) as pdf:
        count = len(pdf.pages)
        for page in pdf.pages:
            txt = page.extract_text()
            if txt:
                pages.append(txt)
    return "\n".join(pages), count


def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
    """
    Extract full text from a PDF file.
    Returns (full_text, page_count).
    Tries PyMuPDF first, falls back to pdfplumber.
    """
    if _HAS_FITZ:
        try:
            text, count = _extract_with_fitz(file_path)
            if len(text.strip()) > 100:
                return _clean_raw_text(text), count
        except Exception:
            pass
    if _HAS_PDFPLUMBER:
        text, count = _extract_with_pdfplumber(file_path)
        return _clean_raw_text(text), count
    raise RuntimeError("No PDF extraction backend available (install PyMuPDF or pdfplumber).")


def _clean_raw_text(text: str) -> str:
    """Remove common PDF extraction artefacts."""
    text = re.sub(r"-\n", "", text)           # hyphenated line breaks
    text = re.sub(r"\f", "\n", text)          # form feeds
    text = re.sub(r"[ \t]{2,}", " ", text)    # multiple spaces
    text = re.sub(r"\n{3,}", "\n\n", text)    # excess blank lines
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # non-ASCII noise
    return text.strip()


# ── Section detection ─────────────────────────────────────────────────────────
def _match_section_header(line: str) -> Optional[str]:
    """
    Try to match a line to a known section name.
    Returns the canonical section name or None.
    """
    stripped = line.strip()
    # Skip very long lines — they're body text, not headers
    if len(stripped) > 120 or len(stripped) < 3:
        return None

    lower = stripped.lower()

    # 1. Exact/prefix keyword match
    for section_name, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if lower == kw or lower.startswith(kw + " ") or lower.startswith(kw + ":"):
                return section_name

    # 2. Numbered heading — extract the label part and re-match
    m = _NUMBERED_SECTION_RE.match(stripped)
    if m:
        label = m.group(2).strip().lower()
        for section_name, keywords in SECTION_KEYWORDS.items():
            for kw in keywords:
                if label == kw or label.startswith(kw):
                    return section_name

    return None


def detect_sections(raw_text: str) -> Dict[str, str]:
    """
    Split raw text into named sections.
    Returns a dict like {"abstract": "...", "methodology": "...", ...}.
    Falls back to {"full_text": raw_text} if no sections are detected.
    """
    lines = raw_text.split("\n")
    sections: Dict[str, list] = {}
    current = "preamble"
    sections[current] = []

    for line in lines:
        matched = _match_section_header(line)
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)

    # Convert to strings, drop empty sections
    result = {}
    for k, v in sections.items():
        text = "\n".join(v).strip()
        if text:
            result[k] = text

    # If only preamble was detected, return full text as a single chunk
    meaningful = {k for k in result if k not in ("preamble", "references")}
    if not meaningful:
        return {"full_text": raw_text}

    return result


# ── Title inference ───────────────────────────────────────────────────────────
def infer_title(raw_text: str) -> str:
    """
    Heuristically infer the paper title from the first non-trivial line.
    - Skips lines that are too short or look like metadata (emails, URLs, page numbers)
    - Stops at "Abstract" if it appears in the first 20 lines
    """
    _skip_re = re.compile(
        r"(http|@|doi:|arxiv:|preprint|submitted|accepted|copyright|©|^\d+$)",
        re.IGNORECASE,
    )
    for line in raw_text.split("\n")[:30]:
        line = line.strip()
        if 15 < len(line) < 220 and not _skip_re.search(line):
            if line.lower().startswith("abstract"):
                break
            return line
    return "Untitled Paper"


# ── Full pipeline ─────────────────────────────────────────────────────────────
async def parse_pdf(file_path: str) -> dict:
    """
    Full pipeline: extract text → detect sections → infer title.
    Returns dict: title, extracted_text, sections (JSON string), page_count.
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
