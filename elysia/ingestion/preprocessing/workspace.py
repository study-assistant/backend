from pathlib import Path

# backend/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PREPROCESSED_DATA_DIR = DATA_DIR / "preprocessed"

# Custom exception for workspace / filesystem errors.
class WorkspaceError(Exception):
    """Raised when a preprocessing workspace cannot be accessed or created."""
    pass

### Validate that the raw data directory exists and is a directory
def validate_raw_data_directory() -> None:
    if not RAW_DATA_DIR.exists():
        raise WorkspaceError(
            f"Raw data directory not found: {RAW_DATA_DIR}"
        )

    if not RAW_DATA_DIR.is_dir():
        raise WorkspaceError(
            f"Raw data path is not a directory: {RAW_DATA_DIR}"
        )

### Create the root directory for preprocessed data
### data/preprocessed
def create_preprocessing_workspace() -> None:
    try:
        PREPROCESSED_DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

    except OSError as e:
        raise WorkspaceError(
            f"Failed to create preprocessing workspace: "
            f"{PREPROCESSED_DATA_DIR}: {e}"
        ) from e

### Create and return the preprocessing directory for a course
### data/preprocessed/course_name
def create_course_workspace(course_slug: str) -> Path:
    try:
        course_dir = PREPROCESSED_DATA_DIR / course_slug
        course_dir.mkdir(parents=True, exist_ok=True)
        return course_dir

    except OSError as e:
        raise WorkspaceError(
            f"Failed to create workspace for {course_slug}: {e}"
        ) from e
