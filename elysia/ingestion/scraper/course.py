from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from utils import extract_primary_course_number

@dataclass
class Course:
    # Core identity
    course_url: str
    course_slug: str
    primary_course_number: str

    # course info
    department_number: Optional[int] = None
    department: Optional[str] = None
    title: Optional[str] = None
    term: Optional[str] = None
    year: Optional[int] = None
    level: Optional[list[str]] = field(default_factory=list)
    course_description: Optional[str] = None
    course_description_html: Optional[str] = None
    instructors: Optional[list[dict]] = field(default_factory=list)
    topics: Optional[list[list[str]]] = field(default_factory=list)
    learning_resource_types: Optional[list[str]] = field(default_factory=list)
    prerequisites: Optional[list[str]] = field(default_factory=list)
    extra_course_numbers: Optional[list[str]] = field(default_factory=list)
    mit_learn_topics: Optional[list[str]] = field(default_factory=list)

    pages: Optional[list[dict]] = field(default_factory=list) # sidebar items
    
    # Local storage
    base_path: Path = None
    pages_path: Path = None
    documents_path: Path = None
    
    # Metadata
    source: str = "MIT OpenCourseWare (https://ocw.mit.edu)"
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    scraper_version: Optional[str] = None

    # Status tracking
    status: str = "pending"  # pending | fetched | partial | failed
    error_message: Optional[str] = None

    
    @classmethod
    def from_url(cls, course_url: str) -> "Course":
        course_url = course_url.rstrip("/") # Normalize URL
        course_slug = course_url.split("/")[-1] # Extract slug

        # Primary course number (reuse your existing logic)
        primary_course_number = extract_primary_course_number(course_url)

        parts = course_slug.split("-")
        # Department number (first numeric part)
        department_number = None
        if parts and parts[0].isdigit():
            department_number = int(parts[0])

        # Term & year (usually last two parts)
        term = None
        year = None
        if len(parts) >= 2 and parts[-1].isdigit():
            year = int(parts[-1])
            term = parts[-2].capitalize()

        return cls(
            course_url=course_url,
            course_slug=course_slug,
            primary_course_number=primary_course_number,
            term=term,
            year=year,
            department_number=department_number,
        )

    # JSON serialization helper
    # Convert Course object to a JSON-serializable dict.
    # Handles Path -> str and datetime -> ISO string conversions.
    def to_json(self) -> Dict[str, Any]:
        d = asdict(self)
        d["fetched_at"] = self.fetched_at.isoformat()
        # Convert Path objects to strings
        for key in ["base_path", "pages_path", "documents_path"]:
            if d[key]:
                d[key] = str(d[key])
        return d
    
    # Safe JSON serialization
    def to_dict(self):
        d = asdict(self)
        d["fetched_at"] = self.fetched_at.isoformat()
        d["base_path"] = str(self.base_path) if self.base_path else None
        d["pages_path"] = str(self.pages_path) if self.pages_path else None
        d["documents_path"] = str(self.documents_path) if self.documents_path else None
        return d
