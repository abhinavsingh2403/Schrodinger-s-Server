"""File checksum verification tool.

Streams a file in chunks to compute its MD5 digest and compares it against
an expected MD5 digest without loading the whole file into memory.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


def compute_md5(file_path: Path | str, chunk_size: int = 1024 * 1024) -> str:
    """Stream a file in chunks and compute its lowercase hexadecimal MD5 digest."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    hasher = hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def verify_file(file_path: Path | str, expected_md5: str) -> tuple[bool, str]:
    """Verify file against expected MD5 digest.

    Returns (is_match, computed_md5).
    """
    computed = compute_md5(file_path)
    expected = expected_md5.strip().lower()
    return (computed == expected, computed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify MD5 checksum of a downloaded file by streaming in chunks."
    )
    parser.add_argument("file_path", help="Path to the file to verify")
    parser.add_argument("expected_md5", help="Expected MD5 hexadecimal digest")
    args = parser.parse_args(argv)

    try:
        is_match, computed = verify_file(args.file_path, args.expected_md5)
    except FileNotFoundError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    expected = args.expected_md5.strip().lower()
    if is_match:
        print(f"MATCH: computed={computed} expected={expected}")
        return 0
    else:
        print(f"MISMATCH: computed={computed} expected={expected}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
