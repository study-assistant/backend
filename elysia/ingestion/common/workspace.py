### workspace.py - shared filesystem layout 
# Owns:
#   - project / data / raw / preprocessed root paths
#   - WorkspaceError
# Does NOT own:
#   - stage-specific layouts (pages/, documents/, chunk dirs, ...) -> those live in each stage and are built on top of this module
from pathlib import Path
import re

# locate backend/ folder
PROJECT_ROOT = Path(__file__).resolve().parents[3] 

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PREPROCESSED_DATA_DIR = DATA_DIR / "preprocessed"
CHUNKS_DATA_DIR = DATA_DIR / "chunks"
EMBEDDING_DATA_DIR = DATA_DIR / "embeddings"

# create folders automatically
DATA_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)
PREPROCESSED_DATA_DIR.mkdir(exist_ok=True)
CHUNKS_DATA_DIR.mkdir(exist_ok=True)
EMBEDDING_DATA_DIR.mkdir(exist_ok=True)

### Custom exception for workspace / filesystem errors.
### Raised when a workspace directory cannot be accessed or created.
class WorkspaceError(Exception):
    pass

### Create path (and parents) if missing, return it
def ensure_dir(path: Path) -> Path:    
    try:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as e:
        raise WorkspaceError(f"Failed to create directory {path}: {e}") from e

### Assert path exists and is a directory
def require_dir(path: Path) -> Path:    
    path = Path(path)
    if not path.exists():
        raise WorkspaceError(f"Directory not found: {path}")
    if not path.is_dir():
        raise WorkspaceError(f"Path is not a directory: {path}")
    return path

##### course workspace #####

# Letters, digits, dash, underscore, dot. No leading dot/dash, no separators, no whitespace, no reserved names
# Length capped well under OS limits
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

### Return course_slug if it is safe as a single path component
def _validate_course_slug(course_slug: str) -> str:
    if not isinstance(course_slug, str):
        raise WorkspaceError(f"Course slug must be a string, got {type(course_slug).__name__}")
    if not course_slug:
        raise WorkspaceError("Course slug is empty")
    if not _SLUG_RE.match(course_slug):
        raise WorkspaceError(
            f"Unsafe course slug {course_slug!r}: must match {_SLUG_RE.pattern}"
        )
    if course_slug.lower() in _RESERVED:
        raise WorkspaceError(f"Course slug {course_slug!r} is a reserved name")
    # Belt and braces: reject anything Path would interpret as absolute or as a parent.
    if Path(course_slug).name != course_slug or course_slug in {".", ".."}:
        raise WorkspaceError(f"Course slug {course_slug!r} is not a single path component")
    return course_slug

def _validate_component(name: str, kind: str) -> str:
    if not isinstance(name, str) or not name:
        raise WorkspaceError(f"{kind} name is empty")
    if Path(name).name != name or name in {".", ".."} or "/" in name or "\\" in name:
        raise WorkspaceError(f"{kind} name {name!r} is not a single path component")
    return name

### Create base/<course_slug>/ plus any named subdirs; return a path dict.
def create_course_workspace(base: Path, course_slug: str, subdirs: list[str] = ()) -> dict:
    course_slug = _validate_course_slug(course_slug)
    root = ensure_dir(Path(base) / course_slug)
    paths = {"root": root}
    for name in subdirs:
        paths[_validate_component(name, "subdir")] = ensure_dir(root / name)
    return paths
