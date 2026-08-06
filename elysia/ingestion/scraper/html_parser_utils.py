import os
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin

### extract_text_with_links - Extract text from a tag, preserving links as "text (URL)". Recursively handles <a> tags inside <p> or other tags.
def extract_text_with_links(tag, base_url="https://ocw.mit.edu"):
    parts = []

    for elem in tag.descendants:
        if getattr(elem, "name", None) == "a":
            href = elem.get("href", "")
            if href:
                href = urljoin(base_url, href)  # <- convert relative to absolute
            text = elem.get_text(strip=True).replace("\xa0", " ")
            if href:
                parts.append(f"{text} ({href})")
            else:
                parts.append(text)
        elif isinstance(elem, NavigableString):
            text = str(elem).strip().replace("\xa0", " ")
            if text:
                parts.append(text)
        elif getattr(elem, "name", None) in ["strong", "em", "span"]:
            parts.append(extract_text_with_links(elem)) # handle inline formatting by recursion
    return " ".join(parts)

def extract_table(table):
    headers = []
    thead = table.find("thead")
    if thead:
        header_tr = thead.find("tr")
        headers = [extract_text_with_links(th) for th in header_tr.find_all("th")]

    num_cols = len(headers) if headers else None
    rows = []
    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr"):
        row = []
        for cell in tr.find_all(["td", "th"]):
            text = extract_text_with_links(cell)  # preserve links
            colspan = int(cell.get("colspan", 1))
            row.extend([text] * colspan)

        if any(row):
            if num_cols:
                while len(row) < num_cols:
                    row.append("")
            rows.append(row)
    cleaned_rows = [r for r in rows if r != headers] # Remove repeated headers inside rows
    return {
        "type": "table",
        "headers": headers,
        "rows": cleaned_rows
    }

def extract_list_by_heading(
    label: str, soup: BeautifulSoup, container_class="course-info-content") -> list[str]:
    heading = soup.find(
        ["h3", "h5"],
        string=lambda s: s and s.strip() == label,
    )
    if not heading:
        return []
    container = heading.find_next("div", class_=container_class)
    if not container:
        return []
    return [a.get_text(strip=True) for a in container.select("a")]

def extract_single_by_heading(label: str, soup: BeautifulSoup):
    items = extract_list_by_heading(label, soup)
    return items[0] if items else None

def extract_learning_resource_types(soup: BeautifulSoup) -> list:
    h5 = soup.find("h5", string=lambda s: s and "Learning Resource Types" in s)
    if not h5:
        return []
    container = h5.find_next("div")
    if not container:
        return []

    resources = []
    for span in container.select("span"):
        text = span.get_text(strip=True)
        if text:
            resources.append(text)

    return resources

def normalize_header(text: str) -> str:
    return text.lower().replace("\xa0", " ").replace("#", "").replace(".", "").strip()


###### DOCUMENTS HELPERS ######
# Parse documents data
DOCUMENT_EXTENSIONS = {
    # documents
    ".pdf": "pdf",
    ".txt": "text",
    ".doc": "doc",
    ".docx": "docx",

    ### TODO - later upgrades
    ## spreadsheets / data 
    # ".csv": "csv",
    # ".xls": "excel",
    # ".xlsx": "excel",

    ## archives 
    # ".zip": "zip",
    # ".gz": "archive",
    # ".tar": "archive",
    # ".7z": "archive",
    # ".rar": "archive",

    ## source code (OCW sometimes provides this)
    # ".py": "code"
}

### final document format in documents list in course_page.json files
# {
#     "title": str,
#     "url": str,                  # direct download URL
#     "resource_url": str | None,  # resource landing page
#     "format": str | None,        # pdf, zip, etc.
#     "extension": str | None,
#     "source_page": str,          # where it was linked from
#     "type": str | None,          # Exams, Assignments, etc.
#     "instructor": str | None,
#     "description": str | None,
#     "local_path": str | None,    # pipeline-added fields
#     "file_size": int | None      # pipeline-added fields
# }
def create_document(
    *,
    title: str | None = None,
    url: str | None = None,
    resource_url: str | None = None,
    format: str | None = None,
    extension: str | None = None,
    source_page: str | None = None,
    type: str | None = None,
    instructor: str | None = None,
    description: str | None = None,
) -> dict:
    return {
        "title": title,
        "url": url,                         # download URL known
        "resource_url": resource_url,
        "format": format,
        "extension": extension,
        "source_page": source_page,
        "type": type,                       # resource type - problem set, assignment, exams etc.
        "instructor": instructor,           # video resource pages contain instructor most of the times
        "description": description,         # resource pages contain short resource description most of the times
    }

def get_file_extension(path: str) -> str:
    return os.path.splitext(path)[1].lower()

def is_direct_file(path: str) -> bool:
    return get_file_extension(path) in DOCUMENT_EXTENSIONS

def is_resource_page(path: str) -> bool:
    # OCW convention
    return "/resources/" in path and not is_direct_file(path)
