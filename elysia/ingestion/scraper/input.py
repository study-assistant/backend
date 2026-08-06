import csv
from pathlib import Path

def read_course_links(csv_path: str | Path) -> list[str]:
    csv_path = Path(csv_path)

    with csv_path.open(newline="", encoding="utf-8") as f:
        return [
            row[0].strip()
            for row in csv.reader(f)
            if row
        ]