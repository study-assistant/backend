from pathlib import Path
import json

# Save a dictionary as a JSON file in the specified folder.
def save_json(data: dict, filename: str, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True) # ensure folder exists
    path = folder / filename

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path