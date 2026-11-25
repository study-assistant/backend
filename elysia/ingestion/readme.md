# Data Ingestion

The data ingestion pipeline is responsible for collecting, processing and preparing educational materials from [MIT OpenCourseWare](https://ocw.mit.edu/) for storage in the vector database. Its goal is to transform raw course materials into structured, cleaned and chunked text that can be embedded and used by the study assistant.

---

## Pipeline Overview

```text
MIT OpenCourseWare
        │
        ▼
   Course Scraping
        │
        ▼
   PDF Documents
        │
        ▼
   Text Extraction
        │
        ▼
 PDF Structure Detection
        │
        ▼
    Text Cleaning
        │
        ▼
 Text Normalization
        │
        ▼
      Chunking
        │
        ▼
 Chunked Documents (JSON)
        │
        ▼
  Embedding (BGE-M3)
        │
        ▼
  Vector Database (Weaviate)
```

---


## Pipeline Stages

| Stage | Description |
|---|---|
| **Course Scraping** | Collects course information, metadata and links to educational materials from MIT OpenCourseWare. |
| **Text Extraction** | Extracts text and relevant layout information from PDF documents. |
| **PDF Structure Detection** | Identifies structural elements such as headings, paragraphs, lists, code snippets, equations and tables. |
| **Text Cleaning** | Removes unwanted artifacts introduced during PDF extraction, such as repeated headers, footers and page numbers. |
| **Text Normalization** | Transforms extracted and cleaned content into a consistent representation while preserving its meaning and structure. |
| **Chunking** | Divides processed documents into smaller text segments suitable for embedding and retrieval. |
| **Embedding** | Converts text chunks into vector representations using BGE-M3. |
| **Vector Database** | Stores vector embeddings and associated metadata in Weaviate for semantic search and retrieval. |

---


## Directory Structure

- `common/` – Shared utilities and components used throughout the ingestion pipeline.
- `scraper/` – Responsible for collecting course information and educational materials from MIT OpenCourseWare.
- `preprocessing/` – Handles PDF extraction, structure detection, cleaning, normalization and document preprocessing.
- `preprocessing/chunker/` – Contains chunking strategies and utilities for creating chunks from processed documents.

---


## Running a stage

Each stage exposes one file with a `run()` function. Run any stage as a module from `backend/backend/elysia/`:

    python -m ingestion.scraper.main
    python -m ingestion.preprocessing.pipeline

<!--
python -m ingestion.chunker.pipeline
python -m ingestion.embedding.pipeline
python -m ingestion.indexing.pipeline-->

Relative imports (`from .workspace import …`, `from ..common.workspace import …`) are used throughout; do not run a stage file directly (`python pipeline.py`) — it will fail with "attempted relative import with no known parent package".

---


## Conventions

- **Shared paths & errors** live in `common/workspace.py` (`WorkspaceError`,  `ensure_dir`, `require_dir`, `create_course_workspace`, all `*_DATA_DIR`  constants). Stages never redefine these.
- **Course identity** is the course slug (`6-006-introduction-to-algorithms-fall-2011`), validated once in `common.workspace._validate_course_slug` and used as the single path component under every data root.

- **Stage I/O** lives in each stage's `storage.py` (e.g. `save_json`, `load_json`). ### TODO
- **Stage data types** live in each stage's `model.py`.


---


## Current Status

The ingestion pipeline is being developed incrementally. Currently, the focus is on PDF-based materials and text processing, with chunking, embedding and vector storage being implemented and evaluated progressively. Support for additional content types and more advanced processing techniques may be introduced in later stages.

| Stage           | Package                  | Status         |
|-----------------|--------------------------|----------------|
| Scraper         | `scraper/`               | refactoring    |
| Preprocessing   | `preprocessing/`         | refactoring    |
| Chunking        | `preprocessing/chunker/` | TODO           |
| Embedding       | `embedding/`             | TODO           |
| Indexing        | `indexing/`              | TODO           |

See the `readme.md` inside each stage package for stage-specific details.
