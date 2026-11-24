import json
from pathlib import Path

from ..model import (
    BlockType,
    DocumentMetadata,
    NormalizedBlock,
    NormalizedPage,
)


def load_normalized_document(file_path: Path):

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Convert metadata
    metadata = DocumentMetadata(
        **data["metadata"]
    )

    # Convert pages and blocks
    pages = []

    for page_data in data["pages"]:

        blocks = []

        for block_data in page_data["blocks"]:

            block = NormalizedBlock(
                block_type=BlockType(block_data["block_type"]),
                text=block_data["text"],
                bbox=block_data.get("bbox"),
            )

            blocks.append(block)

        page = NormalizedPage(
            page_number=page_data["page_number"],
            blocks=blocks,
        )

        pages.append(page)

    return metadata, pages
