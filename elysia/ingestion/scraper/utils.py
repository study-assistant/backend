import re
from urllib.parse import urlparse
import unicodedata
from pathlib import Path

# Extract primary course number from course URL.
# Example: https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/-> 6.006    
# Match patterns like:  6-006, 11-522, 22-68j
def extract_primary_course_number(course_url):
    slug = urlparse(course_url).path.rstrip("/").split("/")[-1]

    match = re.match(r"^(\d+)-(\d+[a-zA-Z]?)", slug)
    if not match:
        return None
    major, minor = match.groups()
    return f"{major}.{minor.upper()}"

# Normalize whitespace in extracted text
# - collapse multiple spaces
# - remove newlines/tabs
def clean_text(text: str) -> str:
    if not text:
        return None

    text = (
        text.replace("\xa0", " ")
        .replace("Â", "")
    )

    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None

# Convert arbitrary text to a safe filename
# - removes forbidden characters
# - normalizes unicode
# - replaces spaces with underscores
def safe_filename(text: str, max_length: int = 255) -> str:
    if not text:
        return "untitled"

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s.-]", "", text)
    text = re.sub(r"\s+", "_", text).strip("_")
    return text[:max_length] or "untitled"


# Get a safe filename from a URL. 
# If URL doesn't contain a basename, fallback to title + extension.
def filename_from_url(url: str, title: str = None, extension: str = "") -> str:
    url_path = urlparse(url).path
    basename = Path(url_path).name
    if not basename and title:
        # fallback: slugify the title + extension
        from .utils import slugify
        basename = slugify(title) + extension
    return basename


# Slugify text for IDs, JSON keys, URLs
# Example:
# "Lecture 1: Algorithmic Thinking"
# → lecture-1-algorithmic-thinking
def slugify(text: str, max_length: int = 100) -> str:
    if not text:
        return ""

    text = clean_text(text).lower()

    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    text = re.sub(r"[^\w]+", "-", text) # Replace non-alphanumeric with dashes
    text = text.strip("-") # Remove leading/trailing dashes
    return text[:max_length]
