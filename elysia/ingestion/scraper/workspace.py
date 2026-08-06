### workspace.py - filesystem + layout ###
# example: 
# data/raw/
# └── 6-006-introduction-to-algorithms-fall-2011/
#     ├── course_metadata.json           ← paths['course_metadata']
#     └── pages/                         ← paths['pages']
#            ├── syllabus.json
#            ├── calendar.json
#            └── exams.json
#     ├── documents/                    ← paths['documents']
#            ├── some_txt_file.txt
#            ├── lec01.pdf
#            └── lec02.pdf

from pathlib import Path
from urllib.parse import urlparse
from config import RAW_DATA_DIR

# Custom exception for workspace / filesystem errors.
class WorkspaceError(Exception):
    pass

# Extracts: 6-006-introduction-to-algorithms-fall-2011
def course_slug_from_url(course_url: str) -> str:
    try:
        path = urlparse(course_url).path.rstrip("/")
        if not path.startswith("/courses/"):
            raise ValueError(f"Not a course URL: {course_url}")
        return path.split("/")[-1]
    except Exception as e:
        raise WorkspaceError(f"Failed to extract slug from {course_url}: {e}") from e


# Creates the folder structure for storing:
# - course metadata
# - page JSONs (syllabus, calendar, lectures ...)
# - text documents
# - PDFs
# Returns a dict of paths for scraper to use.
def create_course_workspace(course_slug: str) -> dict:
    try:
        course_dir = RAW_DATA_DIR / course_slug

        paths = {
            "root": course_dir,
            "pages": course_dir / "pages",
            "documents": course_dir / "documents",
            # "pdfs": os.path.join(course_dir, "documents", "pdfs"),
            # "txts": os.path.join(course_dir, "documents", "txts"),
            # "audio": os.path.join(course_dir, "documents", "audio"),
            # "video": os.path.join(course_dir, "documents", "video"),
        }

        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

        return paths

    except OSError as e:
        raise WorkspaceError(
            f"Failed to create workspace for {course_slug}: {e}"
        ) from e