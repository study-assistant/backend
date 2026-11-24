from transformers import PreTrainedTokenizerFast

from ..model import (
    NormalizedPage,
    DocumentMetadata,
)
from .model import (
    BlockReference, DocumentText,
    ChunkingConfig,
    Chunk, ChunkedDocument,
)

class FixedSizeChunker:
    def __init__(
        self,
        tokenizer: PreTrainedTokenizerFast,
        config: ChunkingConfig | None = None,
    ):
        self.tokenizer = tokenizer
        self.config = config or ChunkingConfig()

        self._validate_config()

    def _validate_config(self):
        if self.config.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if self.config.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if self.config.chunk_overlap >= self.config.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size"
            )

    def chunk_document(
        self,
        metadata: DocumentMetadata,
        pages: list[NormalizedPage],
    ) -> ChunkedDocument:

        # 1. Prepare document text and block references
        document = self._prepare_document_text(pages)

        if not document.text.strip():
            return ChunkedDocument(
                document_id=metadata.document_id,
                metadata=metadata,
            )

        # 2. Tokenize the entire document
        encoded = self.tokenizer(
            document.text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )

        input_ids = encoded["input_ids"]
        offsets = encoded["offset_mapping"]

        # 3. Associate tokens with their original blocks
        token_blocks = self._map_tokens_to_blocks(
            offsets,
            document.block_ranges,
        )

        # 4. Create chunks
        chunks = self._create_chunks(
            document_id=metadata.document_id,
            document_text=document.text,
            input_ids=input_ids,
            offsets=offsets,
            token_blocks=token_blocks,
            block_ranges=document.block_ranges,
        )

        return ChunkedDocument(
            document_id=metadata.document_id,
            metadata=metadata,
            chunks=chunks,
        )

    def _prepare_document_text(
        self,
        pages: list[NormalizedPage],
    ) -> DocumentText:

        text_parts = []
        block_ranges = []

        current_position = 0
        global_block_index = 0

        for page in pages:
            for block in page.blocks:

                block_text = block.text

                if not block_text or not block_text.strip():
                    global_block_index += 1
                    continue

                # Separate blocks with two newlines
                if text_parts:
                    separator = "\n\n"
                    text_parts.append(separator)
                    current_position += len(separator)

                start = current_position
                end = start + len(block_text)

                reference = BlockReference(
                    block_index=global_block_index,
                    page_number=page.page_number,
                    block_type=block.block_type,
                    bbox=block.bbox,
                )

                text_parts.append(block_text)

                block_ranges.append(
                    (start, end, reference)
                )

                current_position = end
                global_block_index += 1

        return DocumentText(
            text="".join(text_parts),
            block_ranges=block_ranges,
        )

    def _map_tokens_to_blocks(
        self,
        offsets: list[tuple[int, int]],
        block_ranges: list[
            tuple[int, int, BlockReference]
        ],
    ) -> list[int | None]:

        token_blocks = []
        block_pointer = 0

        for token_start, token_end in offsets:

            # Some tokens may not have a character range
            if token_start == token_end:
                token_blocks.append(None)
                continue

            # Move to the block containing this token
            while (
                block_pointer < len(block_ranges)
                and block_ranges[block_pointer][1] <= token_start
            ):
                block_pointer += 1

            block_index = None

            if block_pointer < len(block_ranges):

                block_start, block_end, reference = (
                    block_ranges[block_pointer]
                )

                if (
                    token_start < block_end
                    and token_end > block_start
                ):
                    block_index = reference.block_index

            token_blocks.append(block_index)

        return token_blocks

    
    def _create_chunks(
        self,
        document_id: str,
        document_text: str,
        input_ids: list[int],
        offsets: list[tuple[int, int]],
        token_blocks: list[int | None],
        block_ranges: list[
            tuple[int, int, BlockReference]
        ],
    ) -> list[Chunk]:

        chunks = []

        total_tokens = len(input_ids)

        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        step = chunk_size - overlap

        # Create a lookup for original block references
        references = {
            reference.block_index: reference
            for _, _, reference in block_ranges
        }

        chunk_index = 0
        start = 0

        while start < total_tokens:

            end = min(start + chunk_size, total_tokens)

            # Get character boundaries from tokenizer offsets
            char_start = offsets[start][0]
            char_end = offsets[end - 1][1]

            # Extract original text, not decoded tokens
            chunk_text = document_text[
                char_start:char_end
            ].strip()

            # Identify unique source blocks
            source_indices = list(dict.fromkeys(
                block_index
                for block_index in token_blocks[start:end]
                if block_index is not None
            ))

            source_references = [
                references[index]
                for index in source_indices
            ]

            # Collect unique pages
            page_numbers = list(dict.fromkeys(
                reference.page_number
                for reference in source_references
            ))

            # Collect unique block types
            block_types = list(dict.fromkeys(
                reference.block_type
                for reference in source_references
            ))

            # Preserve original bounding boxes
            source_bboxes = [
                {
                    "block_index": reference.block_index,
                    "page_number": reference.page_number,
                    "bbox": (
                        list(reference.bbox)
                        if reference.bbox is not None
                        else None
                    ),
                }
                for reference in source_references
            ]

            chunk = Chunk(
                chunk_id=f"{document_id}::chunk::{chunk_index}",
                document_id=document_id,
                chunk_index=chunk_index,
                text=chunk_text,
                page_numbers=page_numbers,
                source_block_indices=source_indices,
                block_types=block_types,
                source_bboxes=source_bboxes,
                token_count=end - start,
            )

            chunks.append(chunk)

            chunk_index += 1

            # Stop when the end of the document is reached
            if end == total_tokens:
                break

            start += step

        return chunks

