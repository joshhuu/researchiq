import re


SECTION_PATTERNS = {
    "abstract": r"(?i)\babstract\b",
    "introduction": r"(?i)\b(introduction|background)\b",
    "methodology": r"(?i)\b(methodology|methods|materials and methods|approach)\b",
    "results": r"(?i)\b(results|findings|experiments)\b",
    "conclusion": r"(?i)\b(conclusion|conclusions|summary|discussion)\b",
}


def clean_text(text: str) -> str:
    """Remove noise from extracted PDF text."""
    text = re.sub(r'\n{3,}', '\n\n', text)        # collapse blank lines
    text = re.sub(r'[ \t]{2,}', ' ', text)          # collapse spaces
    text = re.sub(r'- \n', '', text)                 # fix hyphenated line breaks
    text = re.sub(r'\f', '\n', text)                 # form feeds to newlines
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)      # remove non-ASCII noise
    return text.strip()


def split_into_sections(text: str) -> dict:
    """
    Attempt to split paper text into named sections.
    Falls back to chunking if sections can't be detected.
    """
    lines = text.split('\n')
    sections: dict[str, list[str]] = {k: [] for k in SECTION_PATTERNS}
    sections["other"] = []
    current = "other"

    for line in lines:
        matched = False
        for section, pattern in SECTION_PATTERNS.items():
            # Match short lines that look like headers
            if re.search(pattern, line) and len(line.strip()) < 80:
                current = section
                matched = True
                break
        if not matched:
            sections[current].append(line)

    result = {k: "\n".join(v).strip() for k, v in sections.items() if v}

    # If we couldn't detect sections, fall back to chunking full text
    if not any(result.get(k) for k in ["abstract", "methodology", "results", "conclusion"]):
        chunk = len(text) // 4
        result = {
            "part_1": text[:chunk],
            "part_2": text[chunk:chunk*2],
            "part_3": text[chunk*2:chunk*3],
            "part_4": text[chunk*3:],
        }

    return result


def extract_title(text: str) -> str | None:
    """Heuristic: title is likely the first meaningful line."""
    for line in text.split('\n')[:15]:
        line = line.strip()
        if 10 < len(line) < 200 and not re.match(r'^\d', line):
            return line
    return None
