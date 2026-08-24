from pathlib import Path
import json

from workspace import create_course_workspace
from pdf_extractor import extract_pdf
from text_cleaner import clean_pages
from text_normalizer import normalize_pages
from storage import save_json
from model import CourseProcessingError

def process_course(course_dir: Path) -> None:
    if not course_dir.exists():
        raise CourseProcessingError(
            f"Course directory not found: {course_dir}"
        )

    if not course_dir.is_dir():
        raise CourseProcessingError(
            f"Course path is not a directory: {course_dir}"
        )
    
    # create data/preprocessed/<course_name>
    processed_course_dir = create_course_workspace(course_dir.name)

    pages_dir = course_dir / "pages"
    if not pages_dir.exists():
        print(f"⚠️ No pages directory found for {course_dir.name}")
        return

    page_files = sorted(
        path
        for path in pages_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".json"
    )

    print(f"   Found {len(page_files)} page JSON file(s)")

    for page_file in page_files:
        process_page(page_file, processed_course_dir)


### Process /raw/<course_name>/pages/<page_name>
### process all the documents relevant for that page, save page metadata
def process_page(page_file: Path, processed_course_dir: Path):
    print(f"\t📄 Processing page: {page_file.name}")
    try:
        with page_file.open("r", encoding="utf-8") as file:
            page_data = json.load(file)

    except json.JSONDecodeError as e:
        print(
            f"\t⚠️ Invalid JSON, skipping page: {page_file.name}"
            f"\n\t   Line {e.lineno}, column {e.colno}: {e.msg}"
        )
        return

    except OSError as e:
        print(
            f"\t⚠️ Could not read page, skipping: {page_file.name}"
            f"\n\t   {e}"
        )
        return

    documents = page_data.get("documents", [])

    print(f"\tFound {len(documents)} document(s)")
    for document in documents:
        process_document(
            document=document,
            page_data=page_data,
            processed_course_dir=processed_course_dir,
        )
        

def process_document(
    document: dict,
    page_data: dict, 
    processed_course_dir: Path
):
    # Only process PDFs for now    
    if document.get("format") != "pdf":
        return

    local_path = document.get("local_path")

    if not local_path:
        print(
            f"\t⚠️ PDF document has no local_path: "
            f"{document.get('title', '<unknown>')}"
        )
        return

    pdf_path = Path(local_path)

    if not pdf_path.exists():
        print(f"\t⚠️ PDF file does not exist: {pdf_path}")
        return

    print(f"\t📄 Processing document: {pdf_path}")

    pdf_pages = extract_pdf(pdf_path)
    cleaned_pages = clean_pages(pdf_pages)
    normalized_pages = normalize_pages(cleaned_pages)

    save_processed_document(
        pdf_path=pdf_path,
        processed_pages=normalized_pages,
        processed_course_dir=processed_course_dir,
        document=document,
        page_data=page_data,
    )

def save_processed_document(
    pdf_path: Path, 
    processed_pages, 
    processed_course_dir: Path,
    document: dict,
    page_data: dict):
    
    filename = pdf_path.stem + ".json"
    
    metadata = {
        "document_id": pdf_path.stem, 

        "course": processed_course_dir.name,
        "course_number": page_data.get("primary_course_number"),
        "source_page": page_data.get("page_url"),
        
        "document_title": document.get("title"), 
        "resource_url": document.get("resource_url"),
        
        "format": document.get("format"),
        "source_file": document.get("local_path"),
        "type": document.get("type"),
        "instructor": document.get("instructor"),
        "description": document.get("description"),
    }
    
    data = {
        "metadata": metadata,
        "pages": [page.to_json() for page in processed_pages]
    }

    output_path = save_json(
        data=data,
        filename=filename,
        folder=processed_course_dir,
    )

    print(f"\t💾 Saved: {output_path}")