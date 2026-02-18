#!/usr/bin/env python3
"""
Check coverage of theorem blocks from extracted theorems file against a target file.

Usage:
    python check_coverage.py <theorems_file> <target_file>

Example:
    python check_coverage.py theorems_only/ch3.txt lean_to_nl/ch3_first_order_semantics.md
"""

import sys
import re
from typing import List, Tuple


def extract_theorem_blocks(content: str) -> List[str]:
    r"""
    Extract all \begin{...}...\end{...} blocks from the content.
    Matches theorem, lemma, corollary environments.
    """
    pattern = re.compile(
        r'\\begin\{(theorem|lemma|corollary)\}.*?\\end\{\1\}',
        re.DOTALL
    )
    return [match.group() for match in pattern.finditer(content)]


def check_coverage(theorems_file: str, target_file: str) -> Tuple[List[str], List[str], int]:
    """
    Check if each theorem block from theorems_file appears exactly once in target_file.

    Returns:
        - missing: list of blocks that don't appear in target
        - duplicates: list of blocks that appear more than once
        - total: total number of theorem blocks
    """
    with open(theorems_file, 'r', encoding='utf-8') as f:
        theorems_content = f.read()

    with open(target_file, 'r', encoding='utf-8') as f:
        target_content = f.read()

    blocks = extract_theorem_blocks(theorems_content)

    missing = []
    duplicates = []

    for block in blocks:
        count = target_content.count(block)
        if count == 0:
            missing.append(block)
        elif count > 1:
            duplicates.append(block)

    return missing, duplicates, len(blocks)


def get_block_preview(block: str, max_len: int = 80) -> str:
    """Get a short preview of a block for display."""
    # Get the first line or first max_len chars
    first_line = block.split('\n')[0]
    if len(first_line) > max_len:
        return first_line[:max_len] + "..."
    return first_line


def get_block_label(block: str) -> str:
    """Extract the label from a theorem block if present."""
    label_match = re.search(r'\\label\{([^}]+)\}', block)
    if label_match:
        return label_match.group(1)
    return None


def main():
    if len(sys.argv) != 3:
        print("Usage: python check_coverage.py <theorems_file> <target_file>")
        print("Example: python check_coverage.py theorems_only/ch3.txt lean_to_nl/ch3.md")
        sys.exit(1)

    theorems_file = sys.argv[1]
    target_file = sys.argv[2]

    missing, duplicates, total = check_coverage(theorems_file, target_file)

    # Print summary
    found = total - len(missing)
    print("=" * 60)
    print("COVERAGE CHECK RESULTS")
    print("=" * 60)
    print(f"Theorems file: {theorems_file}")
    print(f"Target file:   {target_file}")
    print("-" * 60)
    print(f"Total theorem blocks:  {total}")
    print(f"Found (exactly once):  {found - len(duplicates)}")
    print(f"Missing:               {len(missing)}")
    print(f"Duplicates:            {len(duplicates)}")
    print(f"Coverage:              {(total - len(missing)) / total * 100:.1f}%" if total > 0 else "N/A")
    print("=" * 60)

    # Print missing blocks
    if missing:
        print("\nMISSING STATEMENTS:")
        print("-" * 60)
        for i, block in enumerate(missing, 1):
            print(f"{i}.")
            print(block)
            print()
            print("-" * 60)

    # Print duplicates
    if duplicates:
        print("\nDUPLICATE STATEMENTS:")
        print("-" * 60)
        for i, block in enumerate(duplicates, 1):
            # Count occurrences in target
            with open(target_file, 'r', encoding='utf-8') as f:
                count = f.read().count(block)
            print(f"{i}. (appears {count} times)")
            print(block)
            print()
            print("-" * 60)

    # Exit with status code based on results
    if missing or duplicates:
        print("-" * 60)
        if missing and duplicates:
            print(f"RESULT: INCOMPLETE - {len(missing)} missing, {len(duplicates)} duplicates")
        elif missing:
            print(f"RESULT: INCOMPLETE - {len(missing)} missing")
        else:
            print(f"RESULT: HAS DUPLICATES - {len(duplicates)} duplicates")
        sys.exit(1)
    else:
        print("\nRESULT: COMPLETE - All statements found exactly once!")
        sys.exit(0)


if __name__ == '__main__':
    main()
