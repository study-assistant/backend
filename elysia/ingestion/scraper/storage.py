import os
import json

# Save a dictionary as a JSON file in the specified folder.
def save_json(data: dict, filename: str, folder: str) -> str:
    os.makedirs(folder, exist_ok=True)  # ensure folder exists
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

# Save plain text content in the specified folder.
def save_text(content: str, filename: str, folder: str) -> str:
    os.makedirs(folder, exist_ok=True)  # ensure folder exists
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
