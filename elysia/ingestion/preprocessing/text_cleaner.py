import re

from model import CleanedPage, TextCleaningError
from model import ExtractedPage

# Clean extracted PDF pages. The meaning and structure of the original text should be preserved. 
# Cleaning includes:
# - removing repeated headers and footers
# - removing page numbers
# - fixing hyphenation caused by line breaks
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

            text = _remove_repeated_slide_titles(text)

            text = _remove_page_numbers(text)

            text = _fix_hyphenation(text)

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
            line = line.rstrip()

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
    line = line.rstrip()
    line = re.sub(r"\s+", " ", line)

    return line.lower()


### Some pdf can have multiple slides on one page - in that case we make sure that header and footer as well as page number is recognized for every slide on page
def _remove_repeated_slide_titles(text: str) -> str:
    lines = text.splitlines()

    # Map title -> slide numbers found on this PDF page.
    title_numbers: dict[str, set[int]] = {}

    for line in lines:
        match = re.match(r"^(.*?)\s+(\d+)\s*$", line.strip())

        if not match:
            continue

        title = match.group(1).strip()
        number = int(match.group(2))

        if not title:
            continue

        normalized_title = _normalize_line_for_comparison(title)

        title_numbers.setdefault(normalized_title, set()).add(number)

    # A title appearing with multiple different numbers on the same PDF page is likely a repeated slide header
    repeated_slide_titles = {
        title
        for title, numbers in title_numbers.items()
        if len(numbers) >= 2
    }

    cleaned_lines = []

    for line in lines:
        match = re.match(r"^(.*?)\s+(\d+)\s*$", line.strip())

        if match:
            title = match.group(1).strip()
            normalized_title = _normalize_line_for_comparison(title)

            if normalized_title in repeated_slide_titles:
                continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


### Remove lines that contain only a page number
def _remove_page_numbers(text: str) -> str:
    lines = []

    for line in text.splitlines():
        stripped = line.rstrip()

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
# def _fix_hyphenation(text: str) -> str:
#     return re.sub(
#         r"(\w)-\n\s*(\w)",
#         r"\1\2",
#         text
#     )
