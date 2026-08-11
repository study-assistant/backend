
from dataclasses import dataclass
from typing import Dict, Any
from pathlib import Path
import pymupdf

### Raised when text cannot be extracted from a PDF
class PDFExtractionError(Exception):
    pass

### Text extracted from a single PDF page
@dataclass
class ExtractedPage:
    page_number: int
    text: str

    def to_json(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
        }
    

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
