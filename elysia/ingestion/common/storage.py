### storage.py - shared file I/O primitives
# Owns:
#   - save_json / save_text / (load_json) over Path-based folders
#   - StorageError on filesystem / serialization failure
# Does NOT own:
#   - stage-specific filename conventions or directory layouts
#   - any business logic about *what* is saved

from pathlib import Path
import json

from .workspace import ensure_dir

### Raised when a file cannot be read, written, or serialized.
class StorageError(Exception):
    pass

### Write data as pretty UTF-8 JSON to folder/filename. Return the path.
def save_json(data: dict, filename: str, folder: Path) -> Path:
    folder = ensure_dir(folder)
    path = folder / filename
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise StorageError(f"Failed to write {path}: {e}") from e
    except (TypeError, ValueError) as e:
        raise StorageError(f"Failed to serialize {path}: {e}") from e
    return path

### Write content as UTF-8 text to folder/filename. Return the path.
def save_text(content: str, filename: str, folder: Path) -> Path:
    folder = ensure_dir(folder)
    path = folder / filename
    try:
        with path.open("w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise StorageError(f"Failed to write {path}: {e}") from e
    return path

### Read and parse a JSON file. Return the parsed object.
### Raises:
###         StorageError: the file could not be read (filesystem failure).
###         json.JSONDecodeError: the file contents are not valid JSON.
def load_json(path: Path) -> dict:
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise StorageError(f"Failed to read {path}: {e}") from e
    except json.JSONDecodeError as e:
        # enrich with the filename — bare JSONDecodeError doesn't know it
        raise json.JSONDecodeError(
            f"Invalid JSON in {path}: {e.msg}", e.doc, e.pos
        ) from e