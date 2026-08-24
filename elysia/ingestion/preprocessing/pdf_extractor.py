from pathlib import Path
import pymupdf

from model import ExtractedPage, PDFExtractionError  

# Extract text from a PDF document page by page. The extracted text is returned without any cleaning or modification.
def extract_pdf(pdf_path: Path) -> list[ExtractedPage]:
    if not pdf_path.exists():
        raise PDFExtractionError(
            f"PDF file not found: {pdf_path}"
        )

    if not pdf_path.is_file():
        raise PDFExtractionError(
            f"PDF path is not a file: {pdf_path}"
        )

    try:
        with pymupdf.open(pdf_path) as pdf:
            pages = []

            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text")

                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=text
                    )
                )

            return pages

    except Exception as e:
        raise PDFExtractionError(
            f"Failed to extract text from PDF: {pdf_path}: {e}"
        ) from e
