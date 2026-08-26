import re
from collections import Counter

from model import (
    ExtractedBlock,ExtractedPage_V1,
    BlockType, StructuredBlock, StructuredPage,
    StructureDetectionError
)

def detect_structure(
    pages: list[ExtractedPage_V1],
) -> list[StructuredPage]:

    if not pages:
        return []

    try:
        structured_pages = []

        for page in pages:
            dominant_font_size = _get_dominant_font_size(
                page
            )

            structured_blocks = []

            for index, block in enumerate(page.blocks):

                block_type, confidence = _classify_block(
                    block, dominant_font_size,
                )
                
                structured_blocks.append(
                    StructuredBlock(
                        block_type=block_type,
                        bbox=block.bbox,
                        source_block_index=index,
                        confidence=confidence,
                        lines=block.lines,
                    )
                )

            structured_pages.append(
                StructuredPage(
                    page_number=page.page_number,
                    width=page.width,
                    height=page.height,
                    blocks=structured_blocks,
                )
            )

        return structured_pages

    except Exception as e:
        raise StructureDetectionError(
            f"Failed to detect document structure: {e}"
        ) from e

def _classify_block(
    block: ExtractedBlock,
    dominant_font_size: float,
) -> tuple[BlockType, float]:
    
    if not block.lines and block.block_type != "1":
        return BlockType.UNKNOWN, 0.0

    # Image
    is_image, confidence = _looks_like_image(block)
    if is_image:
        return BlockType.IMAGE, confidence

    # Code
    is_code, confidence = _looks_like_code(block)
    if is_code:
        return BlockType.CODE, confidence
    
    # Equation
    is_equation, confidence = _looks_like_equation(block)
    if is_equation:
        return BlockType.EQUATION, confidence

    # Table
    is_table, confidence = _looks_like_table(block)
    if is_table:
        return BlockType.TABLE, confidence
    
    # List
    is_list, confidence = _looks_like_list(block)
    if is_list:
        return BlockType.LIST, confidence

    # Heading
    is_heading, confidence = _looks_like_heading(
        block,
        dominant_font_size,
    )
    if is_heading:
        return BlockType.HEADING, confidence

    # Default
    return BlockType.PARAGRAPH, 0.5


######################################################################
########################## HEADING DETECTION #########################
def _get_dominant_font_size(
    page: ExtractedPage_V1,
) -> float:

    font_sizes = []

    for block in page.blocks:
        for line in block.lines:
            for span in line.spans:
                if span.text.strip():
                    font_sizes.append(
                        round(span.font_size, 1)
                    )

    if not font_sizes:
        return 0.0

    counts = Counter(font_sizes)

    return counts.most_common(1)[0][0]

def _is_bold(block: ExtractedBlock) -> bool:

    for line in block.lines:
        for span in line.spans:

            font_name = span.font_name.lower()

            if "bold" in font_name:
                return True

    return False

def _looks_like_heading(
    block: ExtractedBlock,
    dominant_font_size: float,
) -> tuple[bool, float]:

    if not block.lines:
        return False, 0.0

    if dominant_font_size <= 0:
        return False, 0.0

    text = block.text.strip()

    if not text:
        return False, 0.0

    score = 0.0

    # Font size
    font_ratio = (
        block.average_font_size
        / dominant_font_size
    )

    if font_ratio >= 1.5:
        score += 0.5

    elif font_ratio >= 1.25:
        score += 0.3

    elif font_ratio >= 1.15:
        score += 0.15

    # Bold formatting
    if _is_bold(block):
        score += 0.2

    # Number of lines
    if len(block.lines) == 1:
        score += 0.1

    elif len(block.lines) > 3:
        score -= 0.2

    # Text characteristics
    # Shorter text is more likely to be a heading
    if len(text) <= 150:
        score += 0.1

    # Headings usually don't end with punctuation
    if text.endswith((".", ",", ";", ":")):
        score -= 0.1

    # Final decision
    score = max(0.0, min(score, 1.0))

    return score >= 0.5, score

######################################################################
########################### LIST DETECTION ###########################
def _has_list_marker(text: str) -> bool:
    patterns = [
        # Bullet characters
        r"^[•●○▪▫‣⁃]\s+",

        # Hyphen / dash bullets
        r"^[-–—]\s+",

        # Asterisk bullets
        r"^\*\s+",

        # Numbered lists: 1. / 1) / 1:
        r"^\d+[.)]\s+",
        r"^\d+:\s+",

        # Lettered lists: a. / a) / A.
        r"^[a-zA-Z][.)]\s+",

        # Roman numerals: i. / ii. / IV.
        r"^(?=[ivxlcdmIVXLCDM]+[.)]\s)"
        r"[ivxlcdmIVXLCDM]+[.)]\s+",
    ]

    return any(
        re.match(pattern, text)
        for pattern in patterns
    )

def _looks_like_list(
    block: ExtractedBlock,
) -> tuple[bool, float]:

    if not block.lines:
        return False, 0.0

    if len(block.lines) < 1:
        return False, 0.0

    score = 0.0

    list_lines = 0

    for line in block.lines:
        text = line.text.strip()

        if not text:
            continue

        if _has_list_marker(text):
            list_lines += 1

    if list_lines == 0:
        return False, 0.0

    # One marked line is weak evidence.
    if list_lines == 1:
        score += 0.3

    # Multiple marked lines are strong evidence.
    elif list_lines >= 2:
        score += 0.6

    # If most lines in the block are list items, increase confidence.
    non_empty_lines = sum(
        1
        for line in block.lines
        if line.text.strip()
    )

    if non_empty_lines > 0:
        list_ratio = list_lines / non_empty_lines

        if list_ratio >= 0.8:
            score += 0.3

        elif list_ratio >= 0.5:
            score += 0.15

    score = min(score, 1.0)

    return score >= 0.5, score

######################################################################
####################### CODE SNIPPET DETECTION #######################
def _looks_like_code(
    block: ExtractedBlock,
) -> tuple[bool, float]:

    if not block.lines:
        return False, 0.0

    score = 0.0

    non_empty_lines = [
        line
        for line in block.lines
        if line.text.strip()
    ]

    if not non_empty_lines:
        return False, 0.0

    # Signal 1: monospace font
    if _uses_monospace_font(block):
        score += 0.4

    # Signal 2: indentation
    if _has_indented_lines(block):
        score += 0.2

    # Signal 3: programming syntax
    syntax_score = _get_code_syntax_score(block)
    score += syntax_score

    # Signal 4: multiple lines
    if len(non_empty_lines) >= 2:
        score += 0.1

    # Final decision
    score = max(0.0, min(score, 1.0))
    return score >= 0.5, score

def _uses_monospace_font(
    block: ExtractedBlock,
) -> bool:

    for line in block.lines:
        for span in line.spans:

            font_name = span.font_name.lower()

            if any(
                name in font_name
                for name in (
                    "courier",
                    "mono",
                    "consolas",
                    "menlo",
                    "monaco",
                    "source code",
                    "dejavu sans mono",
                )
            ):
                return True

    return False

def _has_indented_lines(
    block: ExtractedBlock,
) -> bool:

    for line in block.lines:

        text = line.text

        if not text.strip():
            continue

        leading_spaces = len(text) - len(text.lstrip(" "))

        if leading_spaces >= 2:
            return True

    return False

def _get_code_syntax_score(
    block: ExtractedBlock,
) -> float:

    text = block.text

    if not text.strip():
        return 0.0

    score = 0.0

    patterns = [
        # Python
        r"\bdef\s+\w+\s*\(",
        r"\bclass\s+\w+",
        r"\bimport\s+\w+",
        r"\bfrom\s+\w+\s+import\b",
        r"\bif\s+.+:",
        r"\bfor\s+\w+\s+in\b",
        r"\bwhile\s+.+:",
        r"\breturn\b",
        r"\btry\s*:",
        r"\bexcept\b",

        # Common programming syntax
        r"\bfunction\s+\w+\s*\(",
        r"\bpublic\s+(static\s+)?\w+",
        r"\bprivate\s+\w+",
        r"\bvoid\s+\w+\s*\(",
        r"\bint\s+\w+\s*[=;]",
        r"\bstring\s+\w+\s*[=;]",

        # Braces / code blocks
        r"\{",
        r"\}",
        
        # Function calls
        r"\w+\s*\([^)]*\)",

        # Assignment
        r"\w+\s*=\s*[^=]",

        # Comments
        r"^\s*(#|//|/\*)",
    ]

    matches = 0

    for pattern in patterns:
        if re.search(pattern, text, re.MULTILINE):
            matches += 1

    # Don't let syntax alone dominate classification.
    if matches >= 3:
        score += 0.3

    elif matches == 2:
        score += 0.2

    elif matches == 1:
        score += 0.1

    return score

######################################################################
########################### IMAGE DETECTION ##########################
def _looks_like_image(
    block: ExtractedBlock,
) -> tuple[bool, float]:

    if block.block_type == "1":
        return True, 1.0

    return False, 0.0

######################################################################
########################### TABLE DETECTION ##########################
# PDF -> text blocks / lines / spans
#                  ↓
# look for groups of lines with
#   ├── multiple columns
#   ├── repeated x positions
#   ├── similar vertical spacing
#   └── short/aligned text
#  ↓
# TABLE
def _looks_like_table(
    block: ExtractedBlock,
) -> tuple[bool, float]:

    if len(block.lines) < 2:
        return False, 0.0

    # A block containing a list marker should not be classified as a table.
    for line in block.lines:
        text = line.text.strip()

        if not text:
            continue

        if _has_list_marker(text):
            return False, 0.0

    score = 0.0

    # Number of columns inferred from span positions
    column_positions = _get_column_positions(block)

    if len(column_positions) >= 2:
        score += 0.4

    # Multiple lines
    if len(block.lines) >= 3:
        score += 0.2

    # Repeated column structure
    if _has_repeated_columns(block):
        score += 0.3

    score = min(score, 1.0)

    return score >= 0.5, score

def _get_column_positions(
    block: ExtractedBlock,
) -> list[float]:

    positions = []

    for line in block.lines:
        for span in line.spans:

            if not span.text.strip():
                continue

            x_position = span.bbox[0]

            positions.append(x_position)

    if not positions:
        return []

    positions.sort()

    return _cluster_positions(positions)

def _cluster_positions(
    positions: list[float],
    tolerance: float = 5.0,
) -> list[float]:

    if not positions:
        return []

    clusters = [[positions[0]]]

    for position in positions[1:]:

        current_cluster = clusters[-1]

        if abs(
            position - current_cluster[-1]
        ) <= tolerance:

            current_cluster.append(position)

        else:
            clusters.append([position])

    return [
        sum(cluster) / len(cluster)
        for cluster in clusters
    ]

def _has_repeated_columns(
    block: ExtractedBlock,
) -> bool:

    line_column_counts = []

    for line in block.lines:

        positions = []

        for span in line.spans:

            if not span.text.strip():
                continue

            positions.append(
                span.bbox[0]
            )

        if positions:
            line_column_counts.append(
                len(
                    _cluster_positions(positions)
                )
            )

    if len(line_column_counts) < 2:
        return False

    multi_column_lines = sum(
        count >= 2
        for count in line_column_counts
    )

    return (
        multi_column_lines
        / len(line_column_counts)
    ) >= 0.6
######################################################################
######################### EQUATION DETECTION #########################
def _looks_like_equation(
    block: ExtractedBlock,
) -> tuple[bool, float]:

    if not block.lines:
        return False, 0.0

    text = block.text.strip()

    if not text:
        return False, 0.0

    score = 0.0

    # Signal 1: mathematical symbols
    if _contains_math_symbols(text):
        score += 0.3

    # Signal 2: equation structure
    if _contains_equation_structure(text):
        score += 0.3

    # Signal 3: mathematical notation
    if _contains_math_notation(text):
        score += 0.2

    # Signal 4: short / isolated block
    if len(block.lines) <= 3:
        score += 0.1

    # # Signal 5: centered-ish text
    # if _looks_like_centered_block(block):
    #     score += 0.1

    score = max(0.0, min(score, 1.0))

    return score >= 0.5, score

def _contains_math_symbols(text: str) -> bool:

    math_symbols = (
        "∑",
        "∏",
        "∫",
        "√",
        "∞",
        "≈",
        "≠",
        "≤",
        "≥",
        "∈",
        "∉",
        "⊂",
        "⊆",
        "∪",
        "∩",
        "→",
        "←",
        "↔",
        "⇒",
        "⇔",
        "±",
        "×",
        "÷",
        "∂",
        "∆",
        "∇",
        "∝",
        "α",
        "β",
        "γ",
        "δ",
        "θ",
        "λ",
        "μ",
        "π",
        "σ",
        "φ",
        "ω",
    )

    return any(
        symbol in text
        for symbol in math_symbols
    )

def _contains_equation_structure(
    text: str,
) -> bool:

    # Equality / inequality
    if re.search(
        r"(?<![=<>])=(?!=)",
        text,
    ):
        return True

    if re.search(
        r"(≤|≥|≠|≈)",
        text,
    ):
        return True

    # Arrow-based mathematical definitions
    if re.search(
        r"(→|⇒|↔|⇔)",
        text,
    ):
        return True

    return False

def _contains_math_notation(
    text: str,
) -> bool:

    patterns = [

        # Superscripts / powers represented as Unicode
        r"[A-Za-z0-9]\s*[²³⁴⁵⁶⁷⁸⁹]",

        # Common complexity notation
        r"\bO\s*\([^)]*\)",

        # Variable with subscript-like notation
        r"[A-Za-z]\s*[_₀₁₂₃₄₅₆₇₈₉]",

        # Fractions represented with slash
        r"\w+\s*/\s*\w+",

        # Common function notation
        r"\b[a-zA-Z]\s*\([^)]*\)\s*[=<>]",

        # Mathematical operator between operands
        r"\w+\s*[+\-*/×÷]\s*\w+",
    ]

    return any(
        re.search(
            pattern,
            text,
        )
        for pattern in patterns
    )
