"""Deterministic generator for Cowrie HoneyFS identity files.

Generates Debian 12 (bookworm) / srv-app-01 personality files in sensor/honeyfs/etc/:
- os-release
- issue
- issue.net
- hostname
- motd

Standard library only, fully deterministic byte-for-byte output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HONEYFS_DIR = PROJECT_ROOT / "sensor" / "honeyfs"

OS_RELEASE_CONTENT = """PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
VERSION="12 (bookworm)"
VERSION_CODENAME=bookworm
ID=debian
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
"""

ISSUE_CONTENT = "Debian GNU/Linux 12 \\n \\l\n"

ISSUE_NET_CONTENT = "Debian GNU/Linux 12\n"

HOSTNAME_CONTENT = "srv-app-01\n"

MOTD_CONTENT = """The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
"""


def build_honeyfs(target_dir: Path | str = DEFAULT_HONEYFS_DIR) -> dict[str, Path]:
    """Generates deterministic Debian 12 HoneyFS files under target_dir/etc/."""
    base = Path(target_dir).resolve()
    etc = base / "etc"
    etc.mkdir(parents=True, exist_ok=True)

    files_written: dict[str, Path] = {}

    files_to_write = {
        "os-release": OS_RELEASE_CONTENT,
        "issue": ISSUE_CONTENT,
        "issue.net": ISSUE_NET_CONTENT,
        "hostname": HOSTNAME_CONTENT,
        "motd": MOTD_CONTENT,
    }

    for name, content in files_to_write.items():
        file_path = etc / name
        file_path.write_text(content, encoding="utf-8", newline="\n")
        files_written[name] = file_path

    return files_written


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HoneyFS Debian 12 identity files")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=DEFAULT_HONEYFS_DIR,
        help="Target HoneyFS root directory (default: sensor/honeyfs)",
    )
    args = parser.parse_args()
    written = build_honeyfs(args.target_dir)
    for name, path in sorted(written.items()):
        print(f"Generated {name} -> {path}")


if __name__ == "__main__":
    main()
