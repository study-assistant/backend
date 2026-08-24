from dataclasses import dataclass
from typing import Dict, Any

##############
### MODELS ###
##############
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
### ERRORS ###
##############
### Raised when text cannot be extracted from a PDF
class PDFExtractionError(Exception):
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