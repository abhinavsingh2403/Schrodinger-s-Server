"""
Lightweight parser and validator for infra/docker-compose.yml.
Used by smoke_test.ps1 and smoke_test.sh.
Zero external pip dependencies (standard library only).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def inspect_compose(compose_path: Path):
    if not compose_path.exists():
        print(f"ERROR:File not found: {compose_path}")
        sys.exit(1)

    lines = compose_path.read_text(encoding="utf-8").splitlines()

    in_services = False
    in_networks = False
    current_service = None
    published_ports = []
    internal_network = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("services:"):
            in_services = True
            in_networks = False
            continue
        elif stripped.startswith("networks:"):
            in_services = False
            in_networks = True
            continue
        elif stripped.startswith("volumes:"):
            in_services = False
            in_networks = False
            continue

        if in_services:
            # Service definition: 2 space indent
            m = re.match(r"^ {2}([a-zA-Z0-9_-]+):", line)
            if m:
                current_service = m.group(1)
            elif '- "' in line and ":" in line:
                pm = re.search(r'-\s*"([^"]+)"', line)
                if pm and current_service:
                    published_ports.append((current_service, pm.group(1)))

        if in_networks:
            if "internal: true" in line:
                internal_network = True

    for service, port_spec in published_ports:
        print(f"PORT:{service}:{port_spec}")

    print(f"INTERNAL_NETWORK:{internal_network}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("infra/docker-compose.yml")
    inspect_compose(path)
