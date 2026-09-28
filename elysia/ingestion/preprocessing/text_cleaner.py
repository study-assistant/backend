import re
import unicodedata

from model import (
    BlockType, TableStructure,
    ExtractedSpan,
    StructuredBlock, StructuredPage,
    CleanedBlock, CleanedPage_V1,
    TextCleaningError,
)

# Text Cleaning
#     ├── structural cleanup / merging
#     └── textual cleanup
# Clean extracted PDF content. The meaning and structure of the original text should be preserved. 
# Cleaning includes:
# - removing repeated headers and footers
# - removing page numbers
# - fixing hyphenation caused by line breaks
# - removing unnecessary empty lines - trailing whitespace and excessive blank lines

# Input data is in StructuredPage, text_cleaner needs to manage spatial data and reconstruct text 
# with indentation for blocks that require that (table, equation, code), clean the text and store it in CleanedPage_V1

def clean_pages(pages: list[StructuredPage],) -> list[CleanedPage_V1]:
    if not pages:
        return []

    try:
        repeated_lines = _find_repeated_lines(pages)
        print("REPEATED LINES \n ", repeated_lines)

        cleaned_pages = []

        for page in pages:
            # Structural cleanup: 1. Remove meaningless blocks
            page.blocks = _remove_empty_blocks(page.blocks)
            
            edge_blocks = _get_edge_blocks(
                page, # meaningful_blocks,
                edge_count=3,
            )

            cleaned_blocks = []

            for block in page.blocks:
                if (block in edge_blocks):
                    ### Remove repeated headers / footers
                    block = _remove_repeated_lines(block, repeated_lines)
                    if block is None:
                        continue
                    
                    ### Remove page numbers 
                    block = _remove_page_numbers(block) 
                    if block is None: 
                        continue
                
                cleaned_block = _clean_block(block)
                if cleaned_block is None:
                    continue

                cleaned_blocks.append(cleaned_block)

            # TODO # Structural cleanup: 2. Merge compatible adjacent blocks
            # merged_blocks = _merge_adjacent_blocks(page.blocks)

            cleaned_pages.append(
                CleanedPage_V1(
                    page_number=page.page_number,
                    blocks=cleaned_blocks,
                )
            )
            
        return cleaned_pages

    except Exception as e:
        raise TextCleaningError(
            f"Failed to clean structured pages: {e}"
        ) from e


###########################################################
###                  Structural cleanup                 ###
###########################################################
### 1. Remove meaningless blocks - get rid of meaningless, empty blocks that don't contain any data value 
def _remove_empty_blocks(
    blocks: list[StructuredBlock],
) -> list[StructuredBlock]:
    return [
        block
        for block in blocks
        if _block_has_meaningful_content(block)
    ]
def _block_has_meaningful_content(
    block: StructuredBlock,
) -> bool:
    for line in block.lines:
        for span in line.spans:
            if span.text.rstrip():
                return True

    return False

# 2. Merge compatible adjacent blocks - Merge two consecutive blocks if they have the same semantic type, 
# are vertically close, and start approximately at the same horizontal position.
### TODO - consider if this is good for paragraph blocks
MAX_VERTICAL_GAP = 5.0
MAX_X_DIFFERENCE = 10.0
def _can_merge_blocks(
    first: StructuredBlock,
    second: StructuredBlock,
) -> bool:
    if first.block_type != second.block_type:
        return False

    first_left = first.bbox[0]
    first_bottom = first.bbox[3]

    second_left = second.bbox[0]
    second_top = second.bbox[1]

    vertical_gap = second_top - first_bottom
    x_difference = abs(second_left - first_left)

    return (
        0 <= vertical_gap <= MAX_VERTICAL_GAP
        and x_difference <= MAX_X_DIFFERENCE
    )
def _merge_adjacent_blocks(
    blocks: list[StructuredBlock],
) -> list[StructuredBlock]:

    if not blocks:
        return []

    merged_blocks = [blocks[0]]

    for current_block in blocks[1:]:
        previous_block = merged_blocks[-1]

        if _can_merge_blocks(previous_block, current_block):
            merged_blocks[-1] = _merge_blocks(
                previous_block,
                current_block,
            )
        else:
            merged_blocks.append(current_block)

    return merged_blocks
def _merge_blocks(first: StructuredBlock, second: StructuredBlock) -> StructuredBlock:
    new_lines = first.lines + second.lines
    return StructuredBlock(
        block_type=first.block_type,
        bbox=[
            min(first.bbox[0], second.bbox[0]),
            min(first.bbox[1], second.bbox[1]),
            max(first.bbox[2], second.bbox[2]),
            max(first.bbox[3], second.bbox[3]),
        ],
        source_block_index=first.source_block_index,
        confidence=max(first.confidence,second.confidence),
        lines=new_lines
        
        ### TODO Table case ?
        # table=first.table or second.table,
    )


###########################################################
###   repeated headers text   /   remove page numbers   ###
###########################################################
def _get_edge_blocks(
    page: StructuredPage,
    edge_count: int = 3,
) -> list[StructuredBlock]:

    blocks = sorted(
        page.blocks,
        key=lambda block: block.bbox[1],
    )
    # if page contains less than 2*edge_count blocks, return all blocks
    if len(blocks) <= 2 * edge_count:
        return blocks

    return blocks[:edge_count] + blocks[-edge_count:]

def _find_repeated_lines(
    pages: list[StructuredPage],
) -> set[str]:
    if not pages:
        return set()
    line_page_counts: dict[str, int] = {}

    # Require the line to appear on a reasonable proportion
    # of pages, but don't make the threshold too strict.
    min_occurrences = max(2, int(len(pages) * 0.5))

    for page in pages:
        page_lines = set()

        candidate_blocks = _get_edge_blocks(page, edge_count=3)

        for block in candidate_blocks:
            if block.block_type not in {
                BlockType.PARAGRAPH,
                BlockType.HEADING,
            }:
                continue

            for line in block.lines:
                normalized = _normalize_line_for_comparison(line.text)

                if not normalized:
                    continue

                page_lines.add(normalized)
            
        # Count each line only once per page
        for line in page_lines:
            line_page_counts[line] = (line_page_counts.get(line, 0) + 1)

    return {
        line
        for line, count in line_page_counts.items()
        if count >= min_occurrences
    }

def _remove_repeated_lines(
    block: StructuredBlock,
    repeated_lines: set[str],
) -> StructuredBlock | None:
    cleaned_lines = []

    for line in block.lines:
        normalized = _normalize_line_for_comparison(line.text)

        if normalized in repeated_lines:
            continue

        cleaned_lines.append(line)

    if not cleaned_lines:
        return None

    return StructuredBlock(
        block_type=block.block_type,
        bbox=block.bbox,
        source_block_index=block.source_block_index,
        confidence=block.confidence,
        lines=cleaned_lines,
        table=block.table,
    )

def _remove_page_numbers(
    block: StructuredBlock,
) -> StructuredBlock | None:
    cleaned_lines = []

    for line in block.lines:
        stripped = line.text.rstrip()

        # Plain page number: 1, 25, 123 ...
        if re.fullmatch(r"\d+", stripped):
            continue

        # Page number formats: 
        # Page 2
        # 2 of 10
        # Page 2 of 10
        if re.fullmatch(
            r"(page\s+)?\d+(\s+of\s+\d+)?",
            stripped,
            re.IGNORECASE,
        ):
            continue

        cleaned_lines.append(line)

    # The whole block contained only page numbers
    if not cleaned_lines:
        return None

    return StructuredBlock(
        block_type=block.block_type,
        bbox=block.bbox,
        source_block_index=block.source_block_index,
        confidence=block.confidence,
        lines=cleaned_lines,
        table=block.table,
    )


###########################################################
###                    Block cleanup                    ###
###########################################################
def _clean_block(block: StructuredBlock) -> CleanedBlock | None:
    # Cleaning rules depend on the type of block.
    block_type = block.block_type
    
    match block_type:
        ### Image blocks might be used later in OCR for some scanned documents
        case BlockType.IMAGE:
            return CleanedBlock(block_type=block_type, text="")

        ### text types: HEADING, LIST, PARAGRAPH
        case BlockType.HEADING | BlockType.PARAGRAPH | BlockType.LIST:
            text = _clean_text(_retrieve_block_text(block))
            if not text:
                return None
            return CleanedBlock(block_type=block_type, text=text)

        case BlockType.CODE:
            return _reconstruct_code_block_text_with_indentation(block)
        
        # case BlockType.TABLE: # TODO
        #     return _clean_table_block(block)

        # case BlockType.EQUATION: # TODO
        #     return _reconstruct_equation_block(block)
        
        # default case
        case _:
            text = _retrieve_block_text(block)
            if not text.strip():
                return None
            return CleanedBlock(block_type=block_type, text=text)


### text types: HEADING, LIST, PARAGRAPH
def _retrieve_block_text(block: StructuredBlock) -> str:
    if not block.lines:
        return ""

    return "\n".join(
        line.text
        for line in block.lines
        if line.text.strip()
    )

def _clean_text(text: str) -> str:
    text = _fix_hyphenation(text)
    text = _clean_whitespace(text)
    return text

def _clean_whitespace(text: str) -> str:
    # Remove spaces at the end of lines
    text = "\n".join(
        line.rstrip()
        for line in text.splitlines()
    )

    # Remove excessive empty lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text

def _fix_hyphenation(text: str) -> str:
    return re.sub(
        r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)",
        "",
        text,
    )
###########################################################
### TODO still needs fixing - line numbers sometimes don't get deleted...
# CODE block:     CODE handling 
            # StructuredBlock(CODE)
            #         ▼
            # sort lines vertically
            #         ▼
            # sort spans horizontally
            #         ▼
            # remove line-number gutter spans
            #         ▼
            # determine indentation from x-position
            #         ▼
            # reconstruct code lines
            #         ▼
            # CleanedBlock

def _is_line_number_span(span: ExtractedSpan) -> bool:
    return bool(
        re.fullmatch(r"\s*\d+\s*", span.text)
    )

def _remove_code_line_number_spans(
    spans: list[ExtractedSpan], has_line_numbers: bool,
    base_x: float,
    gutter_threshold: float = 20.0,
) -> list[ExtractedSpan]:
    if not has_line_numbers or not spans:
        return spans
    
    cleaned_spans = []
    for span in spans:
        if (
            _is_line_number_span(span)
            and span.bbox[0] < base_x - gutter_threshold
        ):
            continue

        cleaned_spans.append(span)
    return cleaned_spans

def _has_code_line_numbers(block: StructuredBlock) -> bool:
    if not block.lines:
        return False

    lines = sorted(block.lines, key=lambda line: line.bbox[1])

    numbers = []
    for line in lines:
        spans = sorted(
            line.spans, key=lambda span: span.bbox[0],
        )

        if not spans:
            continue

        first_span = spans[0]
        text = first_span.text.strip()
        if not re.fullmatch(r"\d+", text):
            continue

        # The numeric span must be near the left edge of the code block.
        if first_span.bbox[0] > block.bbox[0] + 20:
            continue

        numbers.append(int(text))

    if len(numbers) < 2:
        return False

    # Check whether the numbers are mostly sequential.
    sequential_pairs = sum(
        current == previous + 1
        for previous, current in zip(numbers, numbers[1:])
    )

    return sequential_pairs >= max(1, len(numbers) - 2)

def _reconstruct_line_with_spacing(spans: list[ExtractedSpan], space_width: float = 4.5) -> str:
    if not spans:
        return ""

    text = spans[0].text

    for previous, current in zip(spans, spans[1:]):
        previous_x1 = previous.bbox[2]
        current_x0 = current.bbox[0]
        gap = current_x0 - previous_x1
        number_of_spaces = max(0, round(gap / space_width))
        text += " " * number_of_spaces
        text += current.text

    return text.rstrip()

def _reconstruct_code_line(
    spans: list[ExtractedSpan],
    base_x: float,
    block_x0: float,
    has_line_numbers: bool,
    space_width: float = 4.5,
) -> str:
    spans = _remove_code_line_number_spans(spans, has_line_numbers, block_x0)

    if not spans:
        return ""

    spans = sorted(spans, key=lambda span: span.bbox[0])

    first_x = spans[0].bbox[0]
    indentation_width = max(0,first_x - base_x,)
    indentation_spaces = max(0, round(indentation_width / space_width))
    text = " " * indentation_spaces
    text += _reconstruct_line_with_spacing(spans, space_width=space_width)

    return text.rstrip()

def _get_code_base_x(
    visual_lines: list[dict],
    has_line_numbers: bool,
    block_x0: float,
) -> float | None:
    x_positions = []

    for line in visual_lines:
        spans = line["spans"]
        spans = _remove_code_line_number_spans(spans, has_line_numbers, block_x0)

        if not spans:
            continue

        x_positions.append(min(span.bbox[0] for span in spans))

    if not x_positions:
        return None

    return min(x_positions)

def _group_visually_same_lines(ordered_lines, y_tolerance: float = 3.0):
    if not ordered_lines:
        return []

    visual_lines = []

    for spans in ordered_lines:
        if not spans:
            continue

        # Use the first span's y0 as the representative y position.
        current_y = spans[0].bbox[1]

        # If this line is visually on the same row as the previous group, add its spans to that group.
        if visual_lines:
            previous_y = visual_lines[-1]["y"]

            if abs(current_y - previous_y) <= y_tolerance:
                visual_lines[-1]["spans"].extend(spans)
                continue

        # Otherwise, start a new visual line.
        visual_lines.append({
            "y": current_y,
            "spans": list(spans),
        })

    return visual_lines

def _reconstruct_code_block_text_with_indentation(
    block: StructuredBlock,
) -> CleanedBlock:

    if not block.lines:
        return CleanedBlock(
            block_type=block.block_type,
            text="",
        )

    # 1. Sort lines top → bottom.
    lines = sorted(block.lines, key=lambda line: line.bbox[1])

    # 2. Sort spans left → right.
    ordered_lines = []
    for line in lines:
        spans = sorted(line.spans, key=lambda span: span.bbox[0])

        if spans:
            ordered_lines.append(spans)

    # 3. Group visually identical rows.
    visual_lines = _group_visually_same_lines(ordered_lines)

    # 4. Detect whether this code block has line numbers.
    has_line_numbers = _has_code_line_numbers(block)

    # 5. Find the leftmost actual code position.
    base_x = _get_code_base_x(visual_lines, has_line_numbers, block.bbox[0])

    if base_x is None:
        return CleanedBlock(
            block_type=block.block_type,
            text="",
        )

    # 6. Reconstruct each code line.
    reconstructed_lines = []
    for visual_line in visual_lines:
        text = _reconstruct_code_line(
            visual_line["spans"],
            base_x,
            block.bbox[0],
            has_line_numbers,
        )
        reconstructed_lines.append(text)

    # 7. Preserve line breaks, including empty lines.
    text = "\n".join(reconstructed_lines)

    return CleanedBlock(
        block_type=block.block_type,
        text=text,
    )


###########################################################
### TODO table case
def _clean_table_cell(cell: str) -> str:
    cell = cell.replace("\n", " ")
    cell = re.sub(r"\s+", " ", cell)
    return cell.strip()

def _table_to_text(table: TableStructure) -> str:
    rows = table.rows
    if not rows:
        return ""

    lines = []
    for row in rows:
        lines.append(" | ".join(row))
    return "\n".join(lines)

def _clean_table_block(block: StructuredBlock) -> CleanedBlock | None:
    if block.table is None:
        return None

    cleaned_rows: list[list[str]] = []

    for row in block.table.rows:
        cleaned_row = [
            _clean_table_cell(cell)
            for cell in row
        ]

        # Ignore completely empty rows
        if any(cell for cell in cleaned_row):
            cleaned_rows.append(cleaned_row)

    if not cleaned_rows:
        return None

    table = TableStructure(rows=cleaned_rows)
    text = _table_to_text(table)

    if not text:
        return None

    return CleanedBlock(
        block_type=BlockType.TABLE,
        text=text,
        table=table,
    )


# TODO equation case
####################################################################

# Estimate the horizontal distance corresponding to one indentation level.
# For now, use the most common character width among spans.
def _estimate_indentation_width(block: StructuredBlock) -> float:
    character_widths = []

    for line in block.lines:
        for span in line.spans:
            text = span.text

            if not text.strip():
                continue

            if len(text) == 0:
                continue

            width = (
                span.bbox[2] - span.bbox[0]
            )

            character_width = width / len(text)

            if character_width > 0:
                character_widths.append(
                    character_width
                )

    if not character_widths:
        return 10.0

    # Use the median rather than mean so that
    # unusually large spans do not distort the estimate.
    character_widths.sort()

    middle = len(character_widths) // 2

    if len(character_widths) % 2 == 0:
        median = (
            character_widths[middle - 1]
            + character_widths[middle]
        ) / 2
    else:
        median = character_widths[middle]

    # Approximate 4 spaces as one indentation level.
    return median * 4

####################################################################
def _normalize_line_for_comparison(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text) # Replace different kinds of whitespace with one space
    text = text.rstrip() # Remove trailing whitespace
    return text.casefold()