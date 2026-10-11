import unicodedata

from model import CleanedBlock, CleanedPage_V1
from model import BlockType, TableStructure
from model import NormalizedBlock_V1, NormalizedPage_V1, NormalizedDocument, TextNormalizationError

### TODO
# normalize newlines 
# normalize repeated punctuation 
# preserve headings 
# preserve lists 
# preserve tables
# preserve mathematical notation where possible 
# preserve code/examples rather than aggressively modifying them where possible 

def normalize_pages(pages: list[CleanedPage_V1]) -> list[NormalizedPage_V1]:
    if not pages:
        return []

    try:
        normalized_pages = []
        for page in pages:
            
            normalized_blocks = []
            for block in page.blocks:
                if block is None:
                    continue
                
                normalized_block = _normalize_block(block)
                if normalized_block is None:
                    continue

                normalized_blocks.append(normalized_block)

            normalized_pages.append(
                NormalizedPage_V1(
                    page_number=page.page_number,
                    blocks=normalized_blocks,
                )
            )
    
        return normalized_pages
    
    except Exception as e:
        raise TextNormalizationError(
            f"Failed to normalize pages: {e}"
        ) from e

# Normalization rules depend on the type of block.
def _normalize_block(block: CleanedBlock) -> NormalizedBlock_V1 | None:
    block_type = block.block_type

    match block_type:
        ### text types: HEADING, LIST, PARAGRAPH
        case BlockType.HEADING | BlockType.PARAGRAPH | BlockType.LIST:
            text = _normalize_text(block.text)
            if not text:
                return None
            return NormalizedBlock_V1(block_type=block_type, text=text)
        
        # case BlockType.CODE: # TODO
        #     return 
        
        # case BlockType.TABLE: # TODO
        #     return _clean_table_block(block)

        # case BlockType.EQUATION: # TODO
        #     return _reconstruct_equation_block(block)
        
        # default case
        case _:
            text = block.text
            if not text.strip():
                return None
            return NormalizedBlock_V1(block_type=block_type, text=text)

# normalize Unicode characters 
# normalize strange PDF characters such as \u0002 
# normalize whitespace 
def _normalize_text(text: str) -> str:
    text = _normalize_unicode(text)
    text = _remove_control_characters(text)
    text = _normalize_whitespace(text)
    
    return text

def _normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def _remove_control_characters(text: str) -> str:
    return "".join(
        char
        for char in text
        if char in "\n\t" or not unicodedata.category(char).startswith("C")
    )


def _normalize_whitespace(text: str) -> str:
    lines = [
        line.rstrip()
        for line in text.splitlines()
    ]

    while lines and not lines[0].strip():
        lines.pop(0)

    while lines and not lines[-1].strip():
        lines.pop()

    normalized_lines = []
    previous_empty = False

    for line in lines:
        if not line.strip():
            if previous_empty:
                continue

            previous_empty = True
            normalized_lines.append("")
        else:
            previous_empty = False
            normalized_lines.append(line)

    return "\n".join(normalized_lines)