from pathlib import Path
import json
from transformers import AutoTokenizer

from .fixed_token_chunking import FixedSizeChunker
from .model import ChunkingConfig

from .json_loader import load_normalized_document
### 1. Load document
document_path = Path(
    r"C:\Jecka\0_DIPLOMSKI\study-assistant\backend\backend\data\preprocessed\6-006-introduction-to-algorithms-spring-2008\4f64b4e4f7294e986574166085a86c82_recitation12.json"
)
metadata, pages = load_normalized_document(document_path)

### 2. Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    "BAAI/bge-m3",
    use_fast=True,
)

### 3. Configure chunking
config = ChunkingConfig(
    chunk_size=400,
    chunk_overlap=50,
)

### 4. Initialize chunker
chunker = FixedSizeChunker(
    tokenizer=tokenizer,
    config=config,
)

### 5. Chunk document
result = chunker.chunk_document(
    metadata=metadata,
    pages=pages,
)

### 6. Inspect results
print(f"Document: {metadata.document_id}")
print(f"Number of pages: {len(pages)}")
print(f"Number of chunks: {len(result.chunks)}")

for chunk in result.chunks:

    print("\n" + "=" * 60)
    print(f"Chunk: {chunk.chunk_index}")
    print(f"Tokens: {chunk.token_count}")
    print(f"Pages: {chunk.page_numbers}")
    print(f"Blocks: {chunk.source_block_indices}")
    print(f"Types: {chunk.block_types}")
    print("-" * 60)
    print(chunk.text[:500])

### 7. Save the resulting chunks as JSON
with open(
    "_test_chunks.json", 
    "w", 
    encoding="utf-8"
) as file:
    json.dump(
        result.to_json(),
        file,
        ensure_ascii=False,
        indent=2,
    )

print(f"\n\n\nSaved chunks to: _test_chunks.json")