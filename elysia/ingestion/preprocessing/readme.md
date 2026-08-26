# Preprocessing Module

The preprocessing module is responsible for transforming the raw course materials collected by the scraper into clean, structured text that is ready for chunking, embedding generation, and insertion into the vector database.

The preprocessing pipeline follows the **Single Responsibility Principle (SRP)**, where each component performs one well-defined task. This makes the pipeline easier to maintain, test, and extend.

The preprocessing stage preserves important information from the original PDF, such as:

* page numbers
* block boundaries
* line boundaries
* text spans
* bounding boxes
* font information
* document structure
* mathematical notation
* code formatting
* tables
* images

This information can later be used to create better chunks and improve retrieval quality.

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
Structure Detector
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
The preprocessing pipeline is divided into several stages.

The PDF extractor preserves information from the original PDF instead of immediately reducing everything to plain text.

The structure detector identifies logical document structures such as headings, lists, code, equations, tables, and images.

The text cleaner removes artifacts introduced by the PDF layout.

The text normalizer performs conservative normalization while preserving meaningful formatting and structure.

The output of this module is a collection of structured and normalized documents stored in the `data/preprocessed/` directory. These documents serve as the input for the chunking and embedding stages of the ingestion pipeline.

---

## Module Structure

```
preprocessing/
│
├── workspace.py
├── storage.py
├── model.py
├── pdf_extractor.py
├── structure_detection.py
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
| `pdf_extractor.py`                 | PDF → structured raw representation          |
| `structure_detection.py`                 | Detect document structure          |
| `text_cleaner.py`                  | Remove PDF-specific artifacts   |
| `text_normalizer.py`               | Normalize extracted text  |
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

<br>

The models are divided into four groups:

1. **Extraction models**
2. **Structure detection models**
3. **Cleaning models**
4. **Normalization models**

**1. Extraction models**

Extraction models represent the information obtained directly from the PDF while preserving relevant layout and formatting information.

The extraction hierarchy is:

```
ExtractedPage
    │
    └── ExtractedBlock
            │
            └── ExtractedLine
                    │
                    └── ExtractedSpan
```
These models preserve information such as text, page dimensions, bounding boxes, and font information that can be used by later preprocessing stages.


**2. Structure detection models**

Structure detection models represent the semantic type assigned to extracted content.

Supported block types include:
* paragraph
* heading
* list
* code
* equation
* table
* image

`StructuredPage` and `StructuredBlock` preserve the detected structure together with the original extracted information.

**3. Cleaning models**

Cleaning models represent content after PDF-specific artifacts have been removed while preserving the detected document structure.

`StructuredPage → CleanedPage`


**4. Normalization models**

Normalization models represent content after conservative normalization has been applied.

The goal is to make the text representation consistent while preserving its meaning and important document structure.

`CleanedPage → NormalizedBlock`


<br>

The overall model flow is:
```
PDF
 │
 ▼
Extraction - What is on the page?
 │
 ▼
Structure Detection - What kind of thing is it?
 │
 ▼
Cleaning - Remove obvious unwanted artifacts.
 │
 ▼
Normalization - Make representation consistent without changing meaning.
 │
 ▼
Chunking - How should related content be grouped?
```

<br>

Processing errors:

* `PDFExtractionError` — raised when PDF text extraction fails
* `StructureDetectionError` — raised when structure detection fails
* `TextCleaningError` — raised when text cleaning fails
* `TextNormalizationError` — raised when text normalization fails
* `CourseProcessingError` — raised when a course cannot be processed

---

### `pdf_extractor.py`

Extracts information from PDF documents using PyMuPDF.

Responsibilities:

* Open PDF files
* Extract pages
* Extract PDF blocks
* Extract lines
* Extract text spans
* Preserve bounding boxes
* Preserve font information
* Preserve image blocks
* Preserve the original PDF layout information

The extractor intentionally performs minimal modification to the extracted content.

The extraction stage produces a rich representation instead of immediately converting the PDF into plain text.
```
PDF
 │
 ▼
ExtractedPage
 │
 ├── ExtractedBlock
 │      │
 │      ├── ExtractedLine
 │      │      │
 │      │      └── ExtractedSpan
 │      │
 │      └── ...
 │
 └── ...
```
Its primary responsibility is preserving the information contained in the PDF during extraction. This information is particularly important for later detection of:

* headings
* lists
* code
* equations
* tables
* images


---

### `structure_detection.py`
Detects the semantic structure of extracted PDF blocks.

The detector uses rule-based heuristics based on information preserved during PDF extraction.

Current block types:
* PARAGRAPH
* HEADING
* LIST
* CODE
* EQUATION
* TABLE
* IMAGE

Each detected block receives a confidence score.

Current detection approaches include:

* Images — detected using the original PDF block type
* Headings — detected using font size, bold formatting, line count, and text characteristics
* Lists — detected using common bullet, numbered, lettered, and Roman numeral markers
* Code — detected using formatting, indentation, font information, and code-like text characteristics
* Equations — detected using mathematical symbols, equation structure, and mathematical notation
* Tables — detected using multiple lines, column positions, and repeated column structures
* Paragraphs — used as the default classification when no stronger structure is detected

The structure detector is intentionally rule-based so that the behavior can be inspected, tested, and refined using the actual course materials.

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

## Processing Data Flow

The internal representation becomes progressively more structured throughout the preprocessing pipeline:
```
PDF
 │
 ▼
ExtractedPage
 │
 ├── ExtractedBlock
 │      │
 │      ├── ExtractedLine
 │      │      │
 │      │      └── ExtractedSpan
 │      │
 │      └── ...
 │
 ▼
StructuredPage
 │
 ├── StructuredBlock
 │      │
 │      ├── HEADING
 │      ├── PARAGRAPH
 │      ├── LIST
 │      ├── CODE
 │      ├── EQUATION
 │      ├── TABLE
 │      └── IMAGE
 │
 ▼
Cleaned / Normalized Document
 │
 ▼
Chunking
 │
 ▼
Embeddings
```
The important principle is that information should be preserved for as long as possible.

Instead of discarding layout information during PDF extraction, later stages decide which information is useful for cleaning, structure detection, chunking, and retrieval.
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
PDF Extraction
        │
        ▼
Structure Detection
        │
        ▼
Cleaning & Normalization
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
