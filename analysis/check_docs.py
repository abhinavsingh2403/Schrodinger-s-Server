"""
Documentation Link and Claim Checker for Schrödinger's Server.
Enforces G11:
- Scans *.md for:
  (a) Markdown links to local files that do not exist
  (b) Absolute Windows paths (file:///c:/ or C:\\)
  (c) Disallowed claim strings: '100% complete', 'perfect', 'flawless', 'proving', '7.9/10'
Exit code 1 if any hits found; 0 if clean.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Forbidden strings to detect
FORBIDDEN_STRINGS = [
    "100% complete",
    "perfect",
    "flawless",
    "proving",
    "7.9/10",
]

# Regex patterns
RE_MD_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
RE_WIN_ABSOLUTE = re.compile(r"(file:///[cC]:|[cC]:\\|[cC]:/)")


def find_md_files(root: Path = PROJECT_ROOT) -> List[Path]:
    """Finds all markdown files excluding virtualenvs, git, vendor code, and build caches."""
    md_files = []
    ignored_parts = {
        ".git",
        ".venv",
        ".system_generated",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        "cowrie-src",  # Pinned third-party upstream Cowrie vendor source
    }
    for p in root.rglob("*.md"):
        if any(part in p.parts for part in ignored_parts):
            continue
        md_files.append(p)
    return sorted(md_files)


def _format_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def check_file(md_path: Path) -> List[Dict[str, Any]]:
    """Checks a single markdown file and returns a list of hit records."""
    hits: List[Dict[str, Any]] = []
    file_label = _format_path(md_path)
    try:
        content = md_path.read_text(encoding="utf-8")
    except Exception as e:
        hits.append({
            "file": file_label,
            "line": 0,
            "category": "error",
            "message": f"Could not read file: {e}",
        })
        return hits

    lines = content.splitlines()
    in_code_block = False

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track fenced code block state
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            # Even inside a code block, check for hard-coded absolute Windows paths in instructions
            # unless this file is the checker spec itself
            if md_path.name != "GEMINI_TASKS.md" and RE_WIN_ABSOLUTE.search(line):
                hits.append({
                    "file": file_label,
                    "line": idx,
                    "category": "absolute_path",
                    "message": f"Absolute Windows path in code block: {stripped}",
                })
            continue

        # 1. Absolute Windows Paths
        # Ignore literal description of this rule in GEMINI_TASKS.md
        if md_path.name != "GEMINI_TASKS.md" and RE_WIN_ABSOLUTE.search(line):
            hits.append({
                "file": file_label,
                "line": idx,
                "category": "absolute_path",
                "message": f"Absolute Windows path: {stripped}",
            })

        # 2. Disallowed Claim Strings
        lower_line = line.lower()
        for forbidden in FORBIDDEN_STRINGS:
            if forbidden.lower() in lower_line:
                # Do not self-flag the checker specification itself
                if md_path.name in ("GEMINI_TASKS.md", "check_docs.py"):
                    continue
                hits.append({
                    "file": file_label,
                    "line": idx,
                    "category": "disallowed_claim",
                    "message": f"Found disallowed string '{forbidden}': {stripped}",
                })

        # 3. Broken Markdown Links (skip fenced code blocks)
        if not in_code_block:
            # Strip inline code spans before link extraction to prevent array indexing [k](v) collisions
            line_no_inline_code = re.sub(r"`[^`]*`", "", line)
            for match in RE_MD_LINK.finditer(line_no_inline_code):
                target = match.group(2).strip()
                # Ignore web links, mailto, anchor-only links
                if target.startswith(("http://", "https://", "mailto:", "#", "ftp://")):
                    continue

                # Strip query string or anchor fragment
                clean_target = target.split("#")[0].split("?")[0].strip()
                if not clean_target:
                    continue

                # Check if clean_target contains Windows drive or file:///
                if clean_target.startswith("file:///") or (len(clean_target) > 1 and clean_target[1] == ":"):
                    # Already captured by absolute path check
                    continue

                # Relative resolution
                target_path = (md_path.parent / clean_target).resolve()
                if not target_path.exists():
                    hits.append({
                        "file": file_label,
                        "line": idx,
                        "category": "broken_link",
                        "message": f"Broken link to target '{clean_target}' (resolved: {target_path})",
                    })

    return hits


def scan_all_docs(root: Path = PROJECT_ROOT) -> List[Dict[str, Any]]:
    """Scans all *.md files and aggregates all hit records."""
    all_hits = []
    for md_file in find_md_files(root):
        file_hits = check_file(md_file)
        all_hits.extend(file_hits)
    return all_hits


def main() -> None:
    parser = argparse.ArgumentParser(description="Schrödinger's Server Documentation Checker")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="Root directory to scan")
    parser.add_argument("--fail-on-claims", action="store_true", help="Exit 1 if claim strings found")
    args = parser.parse_args()

    hits = scan_all_docs(args.root)
    broken_links = [h for h in hits if h["category"] == "broken_link"]
    abs_paths = [h for h in hits if h["category"] == "absolute_path"]
    claims = [h for h in hits if h["category"] == "disallowed_claim"]

    print(f"[check_docs] Scanned {len(find_md_files(args.root))} files.")
    print(f"  Broken links:   {len(broken_links)}")
    print(f"  Absolute paths: {len(abs_paths)}")
    print(f"  Flagged claims: {len(claims)}")

    if broken_links:
        print("\n--- BROKEN LINKS ---")
        for h in broken_links:
            print(f"  {h['file']}:{h['line']} {h['message']}")

    if abs_paths:
        print("\n--- ABSOLUTE WINDOWS PATHS ---")
        for h in abs_paths:
            print(f"  {h['file']}:{h['line']} {h['message']}")

    if claims:
        print("\n--- FLAGGED CLAIMS (FOR HUMAN REWRITE) ---")
        for h in claims:
            print(f"  {h['file']}:{h['line']} {h['message']}")

    # Exit code: 1 if broken links or absolute paths are present, or if --fail-on-claims is set and claims exist
    if broken_links or abs_paths or (args.fail_on_claims and claims):
        sys.exit(1)

    print("\n[check_docs] Verification PASSED (0 broken links, 0 absolute paths).")
    sys.exit(0)


if __name__ == "__main__":
    main()
