from dataclasses import dataclass, field
from typing import Any

from ..preprocessing.model import BlockType, NormalizedBlock, DocumentMetadata


### Fixed token chunking models
############################# Fixed token chunking models #############################
@dataclass
class ChunkingConfig:
    chunk_size: int = 400
    chunk_overlap: int = 50

@dataclass
class BlockReference:
    block_index: int
    page_number: int
    block_type: Any
    bbox: Any

@dataclass
class DocumentText:
    text: str
    block_ranges: list[tuple[int, int, BlockReference]]
#######################################################################################


@dataclass
class Section:
    title: str | None = None
    blocks: list[NormalizedBlock] = field(default_factory=list)
    parent_title: str | None = None

@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str

    # Original document positions
    page_numbers: list[int] = field(default_factory=list)

    # Original normalized blocks represented by this chunk
    source_block_indices: list[int] = field(default_factory=list)
    block_types: list[BlockType] = field(default_factory=list)

    # Bounding boxes of the original content
    source_bboxes: list[dict[str, Any]] = field(default_factory=list)

    # Section context
    section_title: str | None = None
    parent_title: str | None = None

    # Chunk statistics
    token_count: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "page_numbers": self.page_numbers,
            "source_block_indices": self.source_block_indices,
            "block_types": [
                block_type.value
                for block_type in self.block_types
            ],
            "source_bboxes": self.source_bboxes,
            "section_title": self.section_title,
            "parent_title": self.parent_title,
            "token_count": self.token_count,
        }


@dataclass
class ChunkedDocument:
    document_id: str
    metadata: DocumentMetadata
    chunks: list[Chunk] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "metadata": self.metadata.to_json(),
            "chunks": [
                chunk.to_json()
                for chunk in self.chunks
            ],
        }

