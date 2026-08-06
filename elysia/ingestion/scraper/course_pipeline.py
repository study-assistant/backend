from pathlib import Path
from urllib.parse import urljoin
from utils import filename_from_url
from workspace import create_course_workspace
from fetcher import get_soup, download_file
from html_parser import parse_course_info, parse_course_calendar, parse_course_page, parse_resource_page
from storage import save_json
from course import Course

class CoursePipeline:
    def process_course_main_page(self, course_url: str) -> Course:
        course = Course.from_url(course_url)
        try:
            # 1. Create filesystem workspace
            paths = create_course_workspace(course.course_slug)
            course.base_path = Path(paths["root"])
            course.pages_path = Path(paths["pages"])
            course.documents_path = Path(paths["documents"])
            
            # 2. Fetch HTML
            soup = get_soup(course.course_url)

            # 3. Parse course metadata
            course = parse_course_info(course, soup)
            
            # 4. Save course JSON
            save_json(course.to_json(), "course_info.json", course.base_path)

            # 5. Update status
            course.status = "fetched"
            print(f"🔹 Course metadata saved!")
        except Exception as e:
            course.status = "failed"
            course.error_message = str(e)
            print(f"[ERR] Failed to process course {course.course_slug} and save course info : {e}")

        return course

    # handle the calendar page 
    def process_course_calendar(self, course: Course):
        try:
            calendar_url = urljoin(course.course_url + "/", "pages/calendar")
            soup = get_soup(calendar_url)
            calendar_data = parse_course_calendar(soup)
            save_json(
                {"page_url": calendar_url, "primary_course_number": course.primary_course_number, **calendar_data},
                "calendar.json",
                course.base_path
            )
            print(f"📅 Course calendar saved!")
        except Exception as e:
            print(f"[WARN] Failed to process calendar for {course.course_slug}: {e}")
    

    # Resolve documents (resource pages → direct URLs)
    def resolve_resource_in_documents(self, documents: list[dict]) -> list[dict]:
        resolved_resource_documents = []
        for doc in documents:
            # CASE 1: already has direct URL
            if doc.get("url"):
                resolved_resource_documents.append(doc) 
                continue
            # CASE 2: resource page → resolve
            elif doc.get("resource_url"):
                try:
                    resource_soup = get_soup(doc["resource_url"])
                    parsed_docs = parse_resource_page(
                        soup=resource_soup,
                        resource_url=doc["resource_url"],
                        source_page=doc["source_page"]
                    )
                    # merge placeholder + parsed data
                    for parsed in parsed_docs: # merge placeholder + parsed data 
                        merged = {**doc, **parsed} 
                        resolved_resource_documents.append(merged) 
                except Exception as e:
                    print(f"[WARN] Failed to fetch/parse resource page {doc['resource_url']}: {e}")
                    resolved_resource_documents.append(doc) # keep original doc as fallback
            else:
                continue
        return resolved_resource_documents
    
    # Downloads documents and adds additional fields: local_path, size.
    def download_documents(self, course: Course, documents: list[dict], download: bool = True) -> list[dict]:
        final_docs = []
        for doc in documents:
            if download and doc.get("url"):
                basename = filename_from_url(doc["url"], title=doc.get("title"), extension=doc.get("extension", ""))
                dest_path = course.documents_path / basename
                try:
                    download_file(doc["url"], dest_path)
                    doc["local_path"] = str(dest_path)
                    # Convert size to MB
                    size_bytes = dest_path.stat().st_size
                    doc["size(MB)"] = round(size_bytes / (1024 * 1024), 6)  # 6 decimal places
                except Exception as e:
                    print(f"[WARN] Failed to download {doc['title']}: {e}")
                    doc["local_path"] = dest_path
                    doc["size(MB)"] = None
            final_docs.append(doc)
        return final_docs

    def process_course_page(self, course: Course, page_url: str, page_title: str, parent_title: str = None):
        try:
            soup = get_soup(page_url)
            parsed_data = parse_course_page(soup, page_title, page_url, course.primary_course_number)
            parsed_data["parent"] = parent_title

            # Process documents
            resolved_docs = self.resolve_resource_in_documents(parsed_data["documents"]) # Resolve resource URLs in documents
            # Download documents and add local_path and size(MB)
            downloaded_docs = self.download_documents(course, resolved_docs, download=True)
            # Update parsed_data
            parsed_data["documents"] = downloaded_docs

            # Save JSON
            safe_filename = f"{page_title.lower().replace(' ', '_')}.json"
            save_json(parsed_data, safe_filename, course.pages_path)
            print(f"📁 Saved {safe_filename}!")
            
        except Exception as e:
            print(f"[WARN] Failed to process page for {page_title}: {e}")
        
    # Process all sidebar pages for a course (top-level + children).
    def process_all_pages(self, course: Course):
        if not hasattr(course, "pages") or not course.pages:
            print(f"[WARN] No pages found for {course.course_slug}")
            return

        for page in course.pages:
            page_title = page["title"]
            
            print(f"📄 Parsing page: {page_title} ...")
            
            page_url = page["url"]
            self.process_course_page(course, page_url, page_title)

            print(f"✅ Page parsed: {page_title}")

            parent = f"{page_title} ({page_url})"
            # Process child pages
            for child in page.get("children", []):
                child_title = child["title"]
                child_url = child["url"]
                self.process_course_page(course, child_url, child_title, parent)
