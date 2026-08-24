import re
import unicodedata

from model import CleanedPage
from model import NormalizedPage, TextNormalizationError

def normalize_pages(
    pages: list[CleanedPage],
) -> list[NormalizedPage]:

    if not pages:
        return []

    try:
        normalized_pages = []

        for page in pages:
            text = page.text
            # normalize Unicode characters 
            # normalize strange PDF characters such as \u0002 
            # normalize whitespace 
            text = _normalize_unicode(text)
            text = _remove_control_characters(text)
            text = _normalize_whitespace(text)
            
            ### TODO
            # normalize newlines 
            # normalize repeated punctuation 
            # preserve headings 
            # preserve lists 
            # preserve tables
            # preserve mathematical notation where possible 
            # preserve code/examples rather than aggressively modifying them where possible 
            
            normalized_pages.append(
                NormalizedPage(
                    page_number=page.page_number,
                    text=text
                )
            )

        return normalized_pages

    except Exception as e:
        raise TextNormalizationError(
            f"Failed to normalize pages: {e}"
        ) from e


def _normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def _remove_control_characters(text: str) -> str:
    return "".join(
        char
        for char in text
        if char in "\n\t" or not unicodedata.category(char).startswith("C")
    )


def _normalize_whitespace(text: str) -> str:
    lines = [
        line.rstrip()
        for line in text.splitlines()
    ]

    while lines and not lines[0].strip():
        lines.pop(0)

    while lines and not lines[-1].strip():
        lines.pop()

    normalized_lines = []
    previous_empty = False

    for line in lines:
        if not line.strip():
            if previous_empty:
                continue

            previous_empty = True
            normalized_lines.append("")
        else:
            previous_empty = False
            normalized_lines.append(line)

    return "\n".join(normalized_lines)