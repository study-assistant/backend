import json
import re
import os
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
from course import Course
from config import SCRAPER_VERSION
from html_parser_utils import extract_single_by_heading, extract_list_by_heading, extract_learning_resource_types, extract_text_with_links, extract_table, normalize_header
from html_parser_utils import DOCUMENT_EXTENSIONS, create_document, get_file_extension, is_resource_page, is_direct_file
from utils import clean_text

BASE_URL = "https://ocw.mit.edu"

###### SIDEBAR ######
#### Sidebar handling - fetching pages for the course - checks out all the sidebar items and their children
def parse_sidebar_tree(soup):
    items = []
    # ONLY top-level sections
    for li in soup.select("nav.course-nav > ul > li.course-nav-list-item"):
        parent_div = li.find("div", class_="course-nav-parent")
        if not parent_div:
            continue

        parent_a = parent_div.find("a", href=True)
        if not parent_a:
            continue
        node = {
            "title": parent_a.get_text(strip=True),
            "url": urljoin(BASE_URL, parent_a["href"]),
            "children": []
        }

        # direct children only
        child_ul = li.find("ul", class_="course-nav-child-nav", recursive=False)
        if child_ul:
            for child_li in child_ul.find_all(
                "li", class_="course-nav-list-item", recursive=False
            ):
                child_a = child_li.find("a", href=True)
                if not child_a:
                    continue

                node["children"].append({
                    "title": child_a.get_text(strip=True),
                    "url": urljoin(BASE_URL, child_a["href"]),
                    "children": []
                })
        items.append(node)
    return items

def remove_duplicate_sidebar_items(items):
    seen = set()
    unique_items = []

    for item in items:
        identifier = (item['title'], item['url'])
        if identifier in seen:
            continue  # skip duplicate
        seen.add(identifier)
        # also deduplicate children recursively
        if item['children']:
            item['children'] = remove_duplicate_sidebar_items(item['children'])

        unique_items.append(item)
    return unique_items

def fetch_sidebar_for_course(soup: BeautifulSoup, course: Course):
    sidebar_items = parse_sidebar_tree(soup)
    sidebar_items = remove_duplicate_sidebar_items(sidebar_items)
    course.pages = sidebar_items

#####################################################################
###### COURSE METADATA ######
# fetch course metadata from the main course page
def parse_course_info(course: Course, soup: BeautifulSoup) -> Course:
    # TITLE 
    h1 = soup.find("h1")
    course.title = h1.get_text(strip=True) if h1 else None

    # DEPARTMENT
    course.department = extract_single_by_heading("Departments", soup)

    # LEVEL 
    detail = soup.find("span", class_="course-number-term-detail")
    if detail:
        parts = [p.strip() for p in detail.get_text().split("|")]
        if len(parts) >= 3:
            course.level = [parts[2]]

    # DESCRIPTION
    desc_div = soup.find("div", id="expanded-description") or soup.find("div", id="collapsed-description")
    if desc_div:
        # remove "Show less" button
        for btn in desc_div.select("button"):
            btn.decompose()
    course.course_description = desc_div.get_text(" ", strip=True) if desc_div else None
    course.course_description_html = desc_div.decode_contents() if desc_div else None

    # INSTRUCTORS 
    instructors_raw = (
        extract_list_by_heading("Instructors", soup)
        or extract_list_by_heading("Instructor", soup)
    )
    instructors = []
    for full in instructors_raw:
        parts = full.replace(".", "").split()
        salutation = parts[0] + "." if parts else ""
        first = parts[1] if len(parts) > 1 else ""
        last = parts[-1] if len(parts) > 0 else ""
        instructors.append({
            "first_name": first,
            "last_name": last,
            "middle_initial": "",
            "salutation": salutation,
            "title": full
        })
    course.instructors = instructors

    # TOPICS (hierarchical)
    topics = []
    seen = set()
    current_path = []
    for a in soup.select("a.course-info-topic"):
        text = a.get_text(strip=True)
        if text and text not in seen:
            seen.add(text)
            current_path.append(text)
    if current_path:
        topics.append(current_path)
    course.topics = topics

    # LEARNING RESOURCE TYPES 
    course.learning_resource_types = extract_learning_resource_types(soup)

    # PAGES (sidebar items)
    fetch_sidebar_for_course(soup, course)

    # SCRAPER VERSION
    course.scraper_version = SCRAPER_VERSION
    
    return course

#####################################################################
###### CALENDAR ######
def canonical_key(header: str) -> Optional[str]:
    header = header.lower()
    if header.startswith("lec") or header.startswith("ses"):
        return "session_label"
    if "topic" in header:
        return "topics"
    if "date" in header:
        return "key_dates"
    return None

# Parse a course calendar page into structured data.
def parse_course_calendar(soup: BeautifulSoup) -> Dict:
    result: Dict[str, any] = {}
    
    # Extract description above table
    description: Optional[str] = None
    main = soup.find("main", id="course-content-section")
    if main:
        paragraphs: List[str] = []
        for elem in main.find_all(["p", "table"], recursive=False):
            if elem.name == "table":
                break
            text = clean_text(elem.get_text(" ", strip=True))
            if text:
                paragraphs.append(text)
        if paragraphs:
            description = "\n".join(paragraphs)
    
    # Extract calendar table
    table = soup.find("table")
    if not table:
        print("[WARN] Calendar table not found")
        return {"description": description, "calendar": []}
    # Extract calendar table headers
    thead = table.find("thead")
    headers: List[str] = []
    for th in thead.find_all("th"):
        headers.append(normalize_header(th.get_text(" ", strip=True)))

    # Rows
    calendar: List[Dict] = []
    current_unit: Optional[Dict] = None
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        
        # SKIP header / empty rows
        if not cells: 
            continue

        # UNIT ROW
        if len(cells) == 1 and cells[0].has_attr("colspan"):
            current_unit = {
                "unit": clean_text(cells[0].get_text(strip=True)),
                "sessions": []
            }
            calendar.append(current_unit)
            continue

        # Session row
        data: Dict[str, str] = {}
        for i, cell in enumerate(cells):
            if i >= len(headers):
                continue
            key = canonical_key(headers[i])
            if not key:
                continue
            data[key] = clean_text(cell.get_text(" ", strip=True))

        label = data.get("session_label")
        session_number = int(label) if label and label.isdigit() else None
        session = {
            "session_label": label,
            "session_number": session_number,
            "topics": data.get("topics"),
            "key_dates": data.get("key_dates")
        }

        if current_unit is None:
            current_unit = {"unit": None, "sessions": []}
            calendar.append(current_unit)

        current_unit["sessions"].append(session)

    result["description"] = description
    result["calendar"] = calendar
    print("[INFO] Saved CALENDAR")
    return result


#####################################################################
###### DOCUMENTS ######
def extract_documents_from_section(section, page_url: str) -> list[dict]:
    results = []
    seen_urls = set()

    for link in section.find_all("a", href=True):
        href = link["href"].strip()
        if not href:
            continue

        full_url = urljoin(BASE_URL, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        title = link.get_text(" ", strip=True)
        path = urlparse(full_url).path.lower()
        
        # CASE 1: direct file
        if is_direct_file(path):
            ext = get_file_extension(path)
            results.append(
                create_document(
                    title=title or os.path.basename(path),
                    url=full_url,
                    format=DOCUMENT_EXTENSIONS[ext],
                    extension=ext,
                    source_page=page_url,
                )
            )
            continue

        # CASE 2: resource page
        if is_resource_page(path):
            results.append(
                create_document(
                    title=title,
                    resource_url=full_url,
                    source_page=page_url,
                )
            )
    return results


def extract_collection_documents(
    soup: BeautifulSoup,
    page_url: str
) -> List[Dict[str, Any]]:
    results = []
    seen_urls = set()

    resource_items = soup.select(
        ".resource-item"
    )

    for item in resource_items:
        # Find PDF/download link
        download_link = item.select_one("a.resource-thumbnail[href]")

        if not download_link:
            continue

        file_url = urljoin(page_url, download_link["href"])

        # Avoid duplicates
        if file_url in seen_urls:
            continue
        seen_urls.add(file_url)

        # Find resource page link
        resource_link = item.select_one("a.resource-list-title[href]")
        resource_url = None
        title = None

        if resource_link:
            resource_url = urljoin(
                page_url,
                resource_link["href"]
            )
            title = resource_link.get_text(" ", strip=True)

        # Determine file extension
        path = urlparse(file_url).path.lower()
        ext = get_file_extension(path)
        
        # Create document
        results.append(
            create_document(
                title=title or os.path.basename(path),
                url=file_url,
                format=DOCUMENT_EXTENSIONS[ext],
                extension=ext,
                source_page=page_url,
            )
        )
        
    return results

#####################################################################
###### PAGES ######
# Parses a course page HTML and returns structured data.
# Args:
#   soup: BeautifulSoup object of the page.
#   page_title: Optional title of the page (used as default section if headings missing)
# Returns:
#   Dict with keys: content (list of sections), documents (collection of documents/resources, each with metadata and a downloadable artifact)
def parse_course_page(
    soup: BeautifulSoup,
    page_title: str,
    page_url: str,
    primary_course_number: str,
    parent_title: str = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "page_url": page_url,
        "page_title": page_title,
        "primary_course_number": primary_course_number,
        "parent": parent_title,
        "documents": [],
        "content": []
    }

    # SPECIAL CASE: Video gallery page
    if is_video_gallery_page(soup):

        print(
            f"[INFO] Detected video gallery page: "
            f"{page_url}"
        )

        gallery_result = parse_video_gallery_page(
            soup,
            page_url,
            primary_course_number
        )

        result.update(gallery_result)

        # Preserve parent if needed
        result["parent"] = parent_title

        return result

    # SPECIAL CASE: Resource collection page
    if is_resource_collection_page(soup):
        print(
            f"[INFO] Detected resource collection page: "
            f"{page_url}"
        )

        result["content"] = extract_collection_content(
            soup,
            page_title
        )
        result["documents"] = extract_collection_documents(
            soup,
            page_url
        )
        return result
    
    # Find main article content
    article = soup.find("article", class_="content")
    if not article:
        print("[WARN] Article not found on page")
        return result

    main_section = article.find("main", id="course-content-section")
    if not main_section:
        print("[WARN] Main section not found on page")
        return result

    # Parse content into sections
    page_content: List[Dict[str, Any]] = []
    default_section = {"section": page_title or "Main", "content": []}
    page_content.append(default_section)
    current_section = default_section

    for tag in main_section.children:
        tag_name = getattr(tag, "name", None)

        if tag_name in ["h2", "h3"]: # Main section headings
            current_section = {
                "section": tag.get_text(strip=True), 
                "content": []
            }
            page_content.append(current_section)
        elif tag_name in ["h4", "h5"]: # Optional subsection headings, include as content
            if current_section:
                current_section["content"].append(tag.get_text(strip=True))

        elif tag_name == "p":
            text = extract_text_with_links(tag)
            if text:
                if not current_section:
                    current_section = default_section
                current_section["content"].append(text)

        elif tag_name == "ul":
            for li in tag.find_all("li", recursive=False):
                text = extract_text_with_links(li)
                if text:
                    if not current_section:
                        current_section = default_section
                    current_section["content"].append(text)

        elif tag_name == "table":
            table_data = extract_table(tag)
            if table_data:
                if not current_section:
                    current_section = default_section
                current_section["content"].append(table_data)

    # Extract PDFs metadata
    documents: List[Dict[str, str]] = []
    documents = extract_documents_from_section(main_section, page_url)
    result["documents"] = documents
    result["content"] = page_content
    
    return result


# Detects MIT OCW pages where the main course-content-section is empty and the actual content consists of a collection description and resource-item elements.   
def is_resource_collection_page(soup: BeautifulSoup) -> bool:
    main_section = soup.find(
        "main",
        id="course-content-section"
    )

    resource_items = soup.select(
        ".resource-item"
    )

    # Resource collection page:
    # - main is missing or empty
    # - resource items exist
    if resource_items:
        if not main_section:
            return True

        if not main_section.get_text(strip=True):
            return True
    return False

def extract_collection_content(
    soup: BeautifulSoup,
    page_title: str
) -> List[Dict[str, Any]]:
    content = []
    collection_description = soup.select_one(
        ".collection-description"
    )

    if collection_description:
        texts = []

        for element in collection_description.find_all(
            ["p", "li"],
            recursive=True
        ):
            text = extract_text_with_links(
                element
            )

            if text:
                texts.append(text)

        if texts:
            content.append({
                "section": page_title or "Main",
                "content": texts
            })
    return content


### resource pages most of the time contain only one download document button - one resource page = one document
def parse_resource_page(
    soup: BeautifulSoup,
    resource_url: str,
    source_page: str
) -> list[dict]:
    ### handle video gallery pages
    if soup.select_one(".video-page"):
        return [parse_video_page(soup, resource_url, source_page)]

    # Title already fetched, skip
    # Description
    description = None
    desc_label = soup.find("div", class_="label", string="Description:")
    if desc_label:
        desc_content = desc_label.find_next_sibling("div", class_="content")
        if desc_content:
            description = desc_content.get_text(" ", strip=True)

    # Resource type
    resource_type = None
    type_label = soup.find("div", class_="label", string="Resource Type:")
    if type_label:
        type_content = type_label.find_next_sibling("div", class_="content")
        if type_content:
            resource_type = type_content.get_text(strip=True)

    # Find primary download URL
    file_url = None

    # Preferred: explicit download button
    download_link = soup.select_one("a.download-file[href]")
    if download_link:
        file_url = urljoin(resource_url, download_link["href"])
    else:
        # Fallback: iframe (PDF viewer)
        iframe = soup.select_one("iframe[src]")
        if iframe:
            file_url = urljoin(resource_url, iframe["src"])

    if not file_url:
        return []  # resource page with no downloadable file

    path = urlparse(file_url).path.lower()
    ext = get_file_extension(path)

    return [{
        "url": file_url,
        "resource_url": resource_url,
        "format": DOCUMENT_EXTENSIONS.get(ext),
        "extension": ext,
        "source_page": source_page,
        "type": resource_type,
        "instructor": None,        # future video pages
        "description": description
    }]


#### Video gallery page ####
def parse_video_page(soup, resource_url, source_page):
    description, instructor = extract_description_and_instructor(soup)
    
    return {
        "url": extract_transcript_pdf(soup),
        "resource_url": resource_url,
        "source_page": source_page,
        "type": "Video",
        "format": "pdf",
        "extension": ".pdf",
        "description": description,
        "instructor": instructor,
        "youtube_link": extract_youtube_link(soup),
    }

def extract_description_and_instructor(soup):
    desc = soup.select_one(".video-description, .description")
    if not desc:
        return None, None

    text = desc.get_text(" ", strip=True)

    instructor = None
    match = re.search(r"Instructor:\s*([^.,]+)", text)
    if match:
        instructor = match.group(1).strip()
        text = text.replace(match.group(0), "").strip()

    return text, instructor

def extract_transcript_pdf(soup):
    # 1. Standard case: <a href="...pdf">Download transcript</a>
    for a in soup.select("a[href$='.pdf']"):
        text = a.get_text(" ", strip=True).lower()
        if "transcript" in text:
            return urljoin(BASE_URL, a["href"])

    # 2. Language-selection case: <a href="...pdf" ...>English</a>
    for a in soup.select("a[href$='.pdf']"):
        text = a.get_text(" ", strip=True).lower()
        if text == "english":
            return urljoin(BASE_URL, a["href"])

    # 3. Fallback: data-transcriptlink="...pdf"
    player = soup.select_one("[data-transcriptlink]")
    if player:
        transcript_link = player.get("data-transcriptlink")
        if transcript_link:
            return urljoin(BASE_URL, transcript_link)

    return None

def extract_youtube_link(soup):
    # iframe src
    iframe = soup.select_one("iframe[src*='youtube.com']")
    if iframe:
        src = iframe["src"]
        match = re.search(r"/embed/([^?&/]+)", src)
        if match:
            return f"https://www.youtube.com/watch?v={match.group(1)}"

    # data-setup JSON fallback
    player = soup.select_one("[data-setup]")
    if player:
        try:
            data = json.loads(player["data-setup"])
            sources = data.get("sources", [])
            for s in sources:
                if "youtube.com/embed/" in s.get("src", ""):
                    match = re.search(r"/embed/([^?&/]+)", s["src"])
                    if match:
                        return f"https://www.youtube.com/watch?v={match.group(1)}"
        except Exception:
            pass
    return None


def is_video_gallery_page(soup: BeautifulSoup) -> bool:
    return bool(
        soup.select_one(".video-gallery-card")
    )

def parse_video_gallery_page(
    soup: BeautifulSoup,
    page_url: str,
    primary_course_number: str
) -> Dict[str, Any]:

    result = {
        "page_url": page_url,
        "page_title": None,
        "primary_course_number": primary_course_number,
        "documents": [],
        "content": []
    }

    # Page title
    title = soup.select_one(
        "#course-title h2"
    )

    if title:
        result["page_title"] = title.get_text(
            " ",
            strip=True
        )

    # Find all video cards
    video_cards = soup.select(
        ".video-gallery-card"
    )

    for card in video_cards:
        video_link = card.select_one(
            "a.video-link[href]"
        )

        if not video_link:
            continue

        resource_url = urljoin(
            page_url,
            video_link["href"]
        )

        # Video title
        title_element = card.select_one(
            ".video-title"
        )
        title = None
        if title_element:
            title = title_element.get_text(
                " ",
                strip=True
            )

        # Every video contains a transcript pdf file. Store as a resource to be processed later
        result["documents"].append(
            create_document(
                title=title,
                resource_url=resource_url,
                format="",
                source_page=page_url,
                type="Video"
            )
        )
    return result