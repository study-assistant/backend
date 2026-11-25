## Chunking






















## Pipeline Overview

```
PDF
 │
 ▼
Extraction
 │
 ▼
Structure Detection
 │
 ▼
Cleaning
 │
 ▼
Normalization
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
<br>

---

## Module Structure

```
preprocessing/
└── chunker/
    │
    ├── model.py
    ├── json_loader.py
    ├── fixed_token_chunking.py
    └── test_fixed.py
```
---
<!--
## Components

| Component                 | Responsibility          |
| ------------------------- | ----------------------- |
| `model.py`                | Section, Chunk, ChunkedDocument  |
| `tokenizer.py`            | Load BGE-M3 tokenizer and count tokens       |
| `section_builder.py`      | Group normalized blocks into sections  |
| `chunker.py`              |  Main chunking orchestration         |
| `splitter.py`             |  Split oversized sections into smaller pieces        |
| `utils.py`                | Bounding boxes, text assembly, helper functions |


<!--
| `chunker.py` *(later)*             | Clean text → chunks     |
| `embedding_generator.py` *(later)* | Chunks → vectors        |
| `weaviate_uploader.py` *(later)*   | Vectors → Weaviate      |
-->
---
## Chunking process





## First implementation of chunks - Fixed-size chunking

| parameter                 | Initial value           |
| ------------------------- | ----------------------- |
| Chunk size                |              400 tokens |
| Chunk overlap             |               50 tokens |
| Minimum chunk size        |                    None |
| Maximum chunk size        |              400 tokens |

This method of chunking is probably the easiest approach to implement.

The text is split into chunks based on a predefined number of tokens or characters.
Each new chunk starts before the previous one ends, creating overlap.

Advantages:

- Very easy to implement.
- Predictable chunk sizes.
- Works with almost any document.
- Easy to benchmark.

Disadvantages:

- Can split paragraphs, sentences, code, and tables.
- Doesn't understand document structure.
- Can separate headings from their content.

Here it was implemented as a baseline for comparison, but it wouldn't be used as final strategy as its results are very modest.

