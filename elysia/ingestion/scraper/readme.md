# MIT OpenCourseWare Scraper

A modular Python scraper for downloading **course metadata and written materials**
from [MIT OpenCourseWare](https://ocw.mit.edu/).

The scraper is designed with **clean separation of concerns** and **future extensibility**
in mind, making it easy to add new features, formats, or workflows over time.

---
## License & Usage

All scraped materials are intended for **personal and educational use only**.  
Please respect the [MIT OpenCourseWare Terms of Use](https://ocw.mit.edu/terms/), which apply to all content downloaded via this scraper.

> ⚠️ Do not redistribute MIT OCW materials or use them for commercial purposes without permission.

---
## Running the Scraper

1. Add course URLs to `links.csv`
2. Make sure Python 3.10+ is installed along with required packages
3. Run:

```bash
python main.py
```

---
## What This Scraper Does

For each course URL provided, the scraper:

- Downloads **core course metadata**
  - title
  - course number
  - description
  - instructors
- Parses the **course calendar** (tables)
- Traverses course pages via the sidebar
- Extracts **written learning materials**
  - text content
  - PDFs
  - transcripts (when available)
- Saves structured metadata as **JSON**
- Stores downloaded materials on disk using a clean folder layout

> ⚠️ This scraper currently focuses on **written materials only**.  
> Video files are *not* downloaded, but transcripts and metadata may be extracted.

---

## Project Structure

| File | Responsibility | Key Functions |
|:-----|:----------------:|---------------|
| `links.csv` | Input source | List of course URLs |
| `config.py` | Project configuration | `SCRAPER_VERSION, SCRAPER_DIR, PROJECT_ROOT, DATA_DIR, RAW_DATA_DIR, LINKS_FILE` |
| `course.py` | Course data model | `Course` |
| `input.py` | Input handling | `read_course_links` |
| `utils.py` | Shared helpers | `extract_primary_course_number`, `clean_text`, `safe_filename`, `slugify`, `filename_from_url` |
| `fetcher.py` | HTTP fetching & downloads | `get_soup`, `download_file` |
| `storage.py` | Persistence layer | `save_json`, `save_txt` |
| `workspace.py` | Filesystem workspace management | `course_slug_from_url`, `create_course_workspace` |
| `html_parser.py` | HTML → structured data | `parse_sidebar_tree`, `parse_course_info`, `parse_course_calendar`, `parse_course_page`, `parse_resource_page` etc. |
| `html_parser_utils.py` | HTML parsing utilities | `extract_text_with_links`, `extract_table`, `extract_list_by_heading`, `extract_learning_resource_types`, `DOCUMENT_EXTENSIONS` etc.|
| `course_pipeline.py` | High-level workflow | `process_course_main_page`, `process_course_calendar`, `process_all_pages` |
| `main.py` | Application entry point | Orchestrates scraping process |

---
## Folder Layout

All scraped data is stored under the `data/raw/` directory, organized by course.

Each course is saved in its **own subfolder**, identified by a slug derived from the course URL. The structure below shows an **example layout** for a single course.

```text
data/

└── raw/

    └── 6-006-introduction-to-algorithms-fall-2011/

        ├── course_info.json          # Course metadata
        │
        ├── pages/                    # Parsed course pages
        │   ├── syllabus.json
        │   ├── calendar.json
        │   ├── exams.json
        │   ├── assignments.json
        │   └── ...
        │
        └── documents/                # Downloaded course materials
            ├── lecture01.txt
            ├── lecture02.txt
            ├── lec01.pdf
            ├── lec02.pdf
            └── ...
```
---
