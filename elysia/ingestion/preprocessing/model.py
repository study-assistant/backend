from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum

##### OLD MODELS #####
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

### Cleaned text extracted from a single PDF page
@dataclass
class CleanedPage:
    page_number: int
    text: str

    def to_json(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
        }

### Normalized text
@dataclass
class NormalizedPage:
    page_number: int
    text: str

    def to_json(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
        }


##############
### MODELS ###
##############
### EXTRACTION MODELS
# In this stage we don't have clean text data, but structural data that contain a lot of PDF details we will deal with later
# A span is the smallest text unit returned by PyMuPDF.
# A span usually represents text with the same font, font size, and formatting.
@dataclass
class ExtractedSpan:
    text: str
    font_name: str
    font_size: float
    flags: int
    bbox: tuple[float, float, float, float]

    def to_json(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "flags": self.flags,
            "bbox": self.bbox,
        }


# A line contains one or more text spans.
@dataclass
class ExtractedLine:
    text: str
    bbox: tuple[float, float, float, float]
    spans: list[ExtractedSpan] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "spans": [
                span.to_json()
                for span in self.spans
            ],
        }


# A block represents a logical/visual region returned by PyMuPDF.
# PyMuPDF can return different block types:
#     0 = text
#     1 = image
#     2 = other/unused
#     etc.
# For now we preserve the original PyMuPDF block type instead of trying to classify the block ourselves.
@dataclass
class ExtractedBlock:
    block_type: str
    bbox: tuple[float, float, float, float]
    lines: list[ExtractedLine] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(
            line.text
            for line in self.lines
        )

    @property
    def font_sizes(self) -> list[float]:
        return [
            span.font_size
            for line in self.lines
            for span in line.spans
        ]

    @property
    def max_font_size(self) -> float:
        sizes = self.font_sizes
        return max(sizes) if sizes else 0.0

    @property
    def min_font_size(self) -> float:
        sizes = self.font_sizes
        return min(sizes) if sizes else 0.0

    @property
    def average_font_size(self) -> float:
        sizes = self.font_sizes

        if not sizes:
            return 0.0

        return sum(sizes) / len(sizes)

    def to_json(self) -> dict[str, Any]:
        return {
            "block_type": self.block_type,
            "bbox": self.bbox,
            "lines": [
                line.to_json()
                for line in self.lines
            ],
        }


# Structured representation of a single extracted PDF page.
@dataclass
class ExtractedPage_V1:
    page_number: int
    width: float
    height: float
    blocks: list[ExtractedBlock] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "blocks": [
                block.to_json()
                for block in self.blocks
            ],
        }

#####################################################################
### STRUCTURE DETECTION MODELS
class BlockType(str, Enum):
    UNKNOWN = "unknown" 
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST = "list"
    CODE = "code"
    EQUATION = "equation"
    TABLE = "table" # TODO - fine-tuning
    IMAGE = "image"

@dataclass
class TableStructure:
    rows: list[list[str]]

    def to_json(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
        }

@dataclass
class StructuredBlock:
    block_type: BlockType
    bbox: tuple[float, float, float, float]
    source_block_index: int = -1
    confidence: float = 0.0
    lines: list[ExtractedLine] = field(default_factory=list)
    table: TableStructure | None = None

    
    @property
    def text(self) -> str:
        return "\n".join(
            line.text
            for line in self.lines
        )

    def to_json(self) -> dict[str, Any]:
        data = {
            "block_type": self.block_type.value,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "source_block_index": self.source_block_index,
            "lines": [
                line.to_json()
                for line in self.lines
            ],
        }

        if self.table is not None:
            data["table"] = self.table.to_json()

        return data

@dataclass
class StructuredPage:
    page_number: int
    width: float
    height: float
    blocks: list[StructuredBlock]

    def to_json(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "blocks": [
                block.to_json()
                for block in self.blocks
            ],
        }
#####################################################################
### CLEANING MODELS
@dataclass
class CleanedBlock:
    block_type: BlockType
    text: str
    table: TableStructure | None = None

    def to_json(self) -> dict[str, Any]:
        data = {
            "block_type": self.block_type.value,
            "text": self.text,
        }

        if self.table is not None:
            data["table"] = self.table.to_json()

        return data

@dataclass
class CleanedPage_V1:
    page_number: int
    blocks: list[CleanedBlock]

    def to_json(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "blocks": [
                block.to_json()
                for block in self.blocks
            ],
        }

#####################################################################
### NORMALIZATION MODELS
@dataclass
class NormalizedBlock:
    block_type: str
    text: str
    bbox: tuple[float, float, float, float]
    metadata: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "block_type": self.block_type,
            "text": self.text,
            "bbox": self.bbox,
            "metadata": self.metadata
        }

##############
### ERRORS ###
##############
### Raised when text cannot be extracted from a PDF
class PDFExtractionError(Exception):
    pass

### Raised when document structure detection fails
class StructureDetectionError(Exception):
    pass

### Raised when text cleaning fails
class TextCleaningError(Exception):
    pass

### Raised when text normalizing fails
class TextNormalizationError(Exception):
    pass

### Raised when a course cannot be processed
class CourseProcessingError(Exception):
    pass