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


from model import (
    ExtractedSpan, ExtractedLine, ExtractedBlock, 
    ExtractedPage_V1,
    PDFExtractionError,
)

# Extract a PDF into a structured representation.
# The extraction stage does not clean, normalize, or modify the extracted text.
# It preserves:
#     - page dimensions
#     - block boundaries
#     - line boundaries
#     - span boundaries
#     - font information
#     - font size
#     - formatting flags
#     - bounding boxes
def extract_pdf_V1(pdf_path: Path) -> list[ExtractedPage]:
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

            pages: list[ExtractedPage] = []

            for page_number, page in enumerate(pdf, start=1):
                page_data = page.get_text("dict", sort=True)

                blocks: list[ExtractedBlock] = []

                for block in page_data.get("blocks", []):

                    block_type = block.get("type")

                    bbox = tuple(
                        block.get(
                            "bbox",
                            (0.0, 0.0, 0.0, 0.0)
                        )
                    )

                    lines: list[ExtractedLine] = []

                    # Non-text blocks do not contain "lines".
                    if "lines" not in block:
                        blocks.append(
                            ExtractedBlock(
                                block_type=block_type,
                                bbox=bbox,
                                lines=[]
                            )
                        )

                        continue

                    for line in block["lines"]:

                        line_bbox = tuple(
                            line.get(
                                "bbox",
                                (0.0, 0.0, 0.0, 0.0)
                            )
                        )

                        spans: list[ExtractedSpan] = []

                        for span in line.get("spans", []):

                            span_bbox = tuple(
                                span.get(
                                    "bbox",
                                    (0.0, 0.0, 0.0, 0.0)
                                )
                            )

                            spans.append(
                                ExtractedSpan(
                                    text=span.get("text", ""),
                                    font_name=span.get(
                                        "font",
                                        ""
                                    ),
                                    font_size=span.get(
                                        "size",
                                        0.0
                                    ),
                                    flags=span.get(
                                        "flags",
                                        0
                                    ),
                                    bbox=span_bbox,
                                )
                            )

                        if not spans:
                            continue

                        line_text = "".join(
                            span.text
                            for span in spans
                        )

                        lines.append(
                            ExtractedLine(
                                text=line_text,
                                bbox=line_bbox,
                                spans=spans,
                            )
                        )

                    blocks.append(
                        ExtractedBlock(
                            block_type=block_type,
                            bbox=bbox,
                            lines=lines,
                        )
                    )

                pages.append(
                    ExtractedPage_V1(
                        page_number=page_number,
                        width=page.rect.width,
                        height=page.rect.height,
                        blocks=blocks,
                    )
                )

            return pages

    except PDFExtractionError:
        raise

    except Exception as e:
        raise PDFExtractionError(
            f"Failed to extract text from PDF: {pdf_path}: {e}"
        ) from e