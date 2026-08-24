# Preprocessing Module

The preprocessing module is responsible for transforming the raw course materials collected by the scraper into clean, structured text that is ready for chunking, embedding generation, and insertion into the vector database.

The preprocessing pipeline follows the **Single Responsibility Principle (SRP)**, where each component performs one well-defined task. This makes the pipeline easier to maintain, test, and extend.

---

## Pipeline Overview

```
Raw Course
    │
    ▼
Course Processor
    │
    ▼
Page Processor
    │
    ▼
PDF Extractor
    │
    ▼
Text Cleaner
    │
    ▼
Text Normalizer
    │
    ▼
Preprocessed Documents
```

The output of this module is a collection of cleaned documents stored in the `data/preprocessed/` directory. These documents serve as the input for the chunking and embedding stages of the ingestion pipeline.

---

## Module Structure

```
preprocessing/
│
├── workspace.py
├── storage.py
├── model.py
├── pdf_extractor.py
├── text_cleaner.py
├── text_normalizer.py
├── course_processor.py
└── pipeline.py
```

---

## Components

| Component                          | Responsibility          |
| ---------------------------------- | ----------------------- |
| `workspace.py`                     | Paths and directories   |
| `storage.py`                       | Persistence layer       |
| `model.py`                         | Data models and processing errors  |
| `pdf_extractor.py`                 | PDF → raw text          |
| `text_cleaner.py`                  | Raw text → clean text   |
| `text_normalizer.py`               |  Clean text → normalized text  |
| `course_processor.py`              | Process one course      |
| `pipeline.py`                      | Orchestrate all courses |


<!--
| `chunker.py` *(later)*             | Clean text → chunks     |
| `embedding_generator.py` *(later)* | Chunks → vectors        |
| `weaviate_uploader.py` *(later)*   | Vectors → Weaviate      |
-->

### `workspace.py`

Responsibilities:

* Filesystem workspace management
* create directories when necessary
* provide paths to the other components

---

### `storage.py`

Responsibilities:

* Persistence layer
* save_json(data: dict, filename: str, folder: str)

---

### `model.py`

Responsibilities:

* Defining data models used throughout the preprocessing pipeline
* Representing the different stages of text processing
* Defining processing-specific exceptions

Current models:

* **`ExtractedPage`**
    * Represents text extracted directly from a single PDF page.
    * `PDF → ExtractedPage`
    * Fields: `page_number`, `text`

<br>

* **`CleanedPage`**
    * Represents text after PDF-specific artifacts have been removed.
    * `ExtractedPage → CleanedPage`
    * Fields: `page_number`, `text`

<br>

* **`NormalizedPage`**
    * Represents cleaned text after normalization.
    * `CleanedPage → NormalizedPage`
    * Fields: `page_number`, `text`

Processing errors:

* `PDFExtractionError` — raised when PDF text extraction fails
* `TextCleaningError` — raised when text cleaning fails
* `TextNormalizationError` — raised when text normalization fails
* `CourseProcessingError` — raised when a course cannot be processed

---

### `pdf_extractor.py`

Extracts text from PDF documents.

Responsibilities:

* Open PDF files
* Extract text page by page
* Preserve page-level information
* Return the extracted text without modifying it

This component **does not**:

* remove headers
* remove footers
* clean formatting
* perform chunking
* generate embeddings

Its only responsibility is text extraction.

---

### `text_cleaner.py`

Transforms raw extracted text into clean text by removing formatting artifacts introduced by the PDF layout while preserving the original meaning and structure of the document.
Typical cleaning operations include:
* removing repeated headers
* removing repeated footers
* removing page numbers
* fixing broken line wraps
* removing hyphenation caused by line breaks
* removing PDF extraction artifacts
* removing unnecessary or empty text fragments
* preserving meaningful document structure such as headings, lists, and paragraphs
The output should preserve the original meaning and structure of the document while removing artifacts caused by the PDF layout and extraction process.

---

### `text_normalizer.py`
Transforms cleaned text into a consistent representation suitable for chunking, embedding generation, and semantic search.
Typical normalization operations include:
* normalizing Unicode characters
* normalizing whitespace and line breaks
* replacing invalid or control characters
* normalizing repeated spaces and punctuation
* standardizing common PDF extraction characters
* repairing common extraction inconsistencies
* preserving meaningful formatting such as headings, lists, code, and mathematical notation
* applying consistent text formatting across documents
Normalization should be conservative and should not alter the meaning of the original content.
The output should contain clean, consistent text that can be reliably passed to the chunking stage.

---

### `course_processor.py`

Processes a single course directory.

Responsibilities:

* Read all page JSON files located in the course's `pages/` directory
* Process each page individually

Pseudo workflow:

```
read page JSON files

for each page
    process_page(page)
```

---

### `pipeline.py`

Coordinates the entire preprocessing workflow.

Responsibilities:

* Iterate through every course in `data/raw/`
* Invoke the course processor for each course
* Manage the preprocessing workflow

Pseudo workflow:

```
for each course
    process_course(course)
```



---

## Output Directory

The preprocessing stage generates cleaned documents inside:

```
data/
└── preprocessed/
    ├── course_1/
    ├── course_2/
    └── ...
```

Each processed document should contain:

* extracted text
* source file information
* course metadata
* page metadata

These cleaned documents become the input for the next stage of the ingestion pipeline.

---

## Future Pipeline

The preprocessing module is only one stage of the complete ingestion workflow.

```
MIT OpenCourseWare
        │
        ▼
Scraper
        │
        ▼
Raw Data
        │
        ▼
Preprocessing
        │
        ▼
Chunking
        │
        ▼
Embedding Generation (BGE-M3)
        │
        ▼
Weaviate Vector Database
```

By separating each stage into independent components, the system remains modular, reusable, and easy to extend with future features such as OCR, table extraction, image processing, or additional document formats.
