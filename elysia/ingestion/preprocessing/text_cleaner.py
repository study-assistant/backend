from dataclasses import dataclass
from typing import Dict, Any
import re

from pdf_extractor import ExtractedPage

### Raised when text cleaning fails
class TextCleaningError(Exception):
    pass

### Cleaned text extracted from a single PDF page
@dataclass
class CleanedPage:
    page_number: int
    text: str

    def to_json(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
        }

# Clean extracted PDF pages. The meaning and structure of the original text should be preserved. 
# Cleaning includes:
# - removing repeated headers and footers
# - removing page numbers
# - fixing hyphenation caused by line breaks
# - normalizing whitespace
# - removing unnecessary empty lines
def clean_pages(pages: list[ExtractedPage]) -> list[CleanedPage]:
    if not pages:
        return []

    try:
        repeated_lines = _find_repeated_lines(pages)

        cleaned_pages = []

        for page in pages:
            text = page.text

            text = _remove_repeated_lines(text, repeated_lines)

            text = _remove_page_numbers(text)

            text = _fix_hyphenation(text)

            text = _normalize_whitespace(text)

            cleaned_pages.append(
                CleanedPage(
                    page_number=page.page_number,
                    text=text
                )
            )

        return cleaned_pages

    except Exception as e:
        raise TextCleaningError(
            f"Failed to clean extracted pages: {e}"
        ) from e


### Find lines that occur on multiple pages. Repeated lines are potential headers or footers.
def _find_repeated_lines(
    pages: list[ExtractedPage],
    min_occurrences: int = 2
) -> set[str]:
    line_counts: dict[str, int] = {}

    for page in pages:
        # Count a line at most once per page.
        lines_on_page = set()

        for line in page.text.splitlines():
            line = line.strip()

            if not line:
                continue

            normalized = _normalize_line_for_comparison(line)

            lines_on_page.add(normalized)

        for line in lines_on_page:
            line_counts[line] = line_counts.get(line, 0) + 1

    return {
        line
        for line, count in line_counts.items()
        if count >= min_occurrences
    }


### Remove lines identified as repeated headers or footers
def _remove_repeated_lines(
    text: str,
    repeated_lines: set[str]
) -> str:
    cleaned_lines = []

    for line in text.splitlines():
        normalized = _normalize_line_for_comparison(line)

        if normalized in repeated_lines:
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


### Normalize a line for comparison with other lines
def _normalize_line_for_comparison(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)

    return line.lower()


### Remove lines that contain only a page number
def _remove_page_numbers(text: str) -> str:
    lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if re.fullmatch(r"\d+", stripped):
            continue

        if re.fullmatch(
            r"(page\s+)?\d+(\s+of\s+\d+)?",
            stripped,
            re.IGNORECASE
        ):
            continue

        lines.append(line)

    return "\n".join(lines)


### Fix words split by a line break.
    # Example:
    #     write-
    #     ups
    # becomes:
    #     writeups
def _fix_hyphenation(text: str) -> str:
    return re.sub(
        r"(\w)-\s*\n\s*(\w)",
        r"\1\2",
        text
    )


### Normalize whitespace while preserving paragraph breaks
def _normalize_whitespace(text: str) -> str:
    # Remove trailing/leading whitespace from lines.
    lines = [
        line.strip()
        for line in text.splitlines()
    ]

    # Remove empty lines at the beginning/end.
    while lines and not lines[0]:
        lines.pop(0)

    while lines and not lines[-1]:
        lines.pop()

    # Replace multiple consecutive empty lines with one.
    normalized_lines = []
    previous_empty = False

    for line in lines:
        if not line:
            if previous_empty:
                continue

            previous_empty = True
            normalized_lines.append("")
        else:
            previous_empty = False
            normalized_lines.append(line)

    return "\n".join(normalized_lines)
