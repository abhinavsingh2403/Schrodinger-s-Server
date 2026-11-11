"""S3 Spike Part 2: Event-level Day Sample and Schema Verification.

Inspects data_all.zip on Zenodo (Record 21260400) via HTTP Range requests
without downloading the full 19.4 GB archive, fulfilling SPIKES S3 Step 4.
Extracts daily event logs and checks event-level schema for required fields:
hassh, version, width, height, input, group, ts, eventid, session, sensor.
"""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path
import struct
import sys
from typing import Any, Dict, List
import urllib.request
import zlib

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ZENODO_DATA_ALL_URL: str = "https://zenodo.org/records/21260400/files/data_all.zip"
TOTAL_FILE_SIZE: int = 19372965772

REQUIRED_EVENT_FIELDS: List[str] = [
    "ts",
    "eventid",
    "session",
    "sensor",
    "group",
    "hassh",
    "version",
    "width",
    "height",
    "input",
]


def fetch_range(url: str, start: int, end: int) -> bytes:
    """Fetch byte range via HTTP Range header."""
    req = urllib.request.Request(
        url,
        headers={
            "Range": f"bytes={start}-{end}",
            "User-Agent": "Schrodinger-Server-Research/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def list_zip_entries(url: str = ZENODO_DATA_ALL_URL) -> List[Dict[str, Any]]:
    """Parse Zip64 Central Directory from Zenodo data_all.zip via Range request."""
    logger.info("Reading Zip64 Central Directory locator from remote archive...")
    cd_start = 19372959874
    cd_size = 5800

    cd_data = fetch_range(url, cd_start, cd_start + cd_size - 1)
    pos = 0
    entries = []

    while pos < len(cd_data):
        if not cd_data[pos:].startswith(b"PK\x01\x02"):
            break
        (
            sig,
            v_made,
            v_need,
            flag,
            comp_m,
            mtime,
            mdate,
            crc,
            c_size,
            u_size,
            fn_len,
            extra_len,
            comm_len,
            disk_n,
            int_attr,
            ext_attr,
            l_offset,
        ) = struct.unpack("<IHHHHHHIIIHHHHHII", cd_data[pos : pos + 46])

        fn = cd_data[pos + 46 : pos + 46 + fn_len].decode("utf-8", errors="replace")
        extra = cd_data[pos + 46 + fn_len : pos + 46 + fn_len + extra_len]

        epos = 0
        actual_c_size = c_size
        actual_u_size = u_size
        actual_offset = l_offset

        while epos < len(extra):
            etag, esize = struct.unpack("<HH", extra[epos : epos + 4])
            ebody = extra[epos + 4 : epos + 4 + esize]
            if etag == 1:
                idx = 0
                if u_size == 0xFFFFFFFF:
                    actual_u_size = struct.unpack("<Q", ebody[idx : idx + 8])[0]
                    idx += 8
                if c_size == 0xFFFFFFFF:
                    actual_c_size = struct.unpack("<Q", ebody[idx : idx + 8])[0]
                    idx += 8
                if l_offset == 0xFFFFFFFF:
                    actual_offset = struct.unpack("<Q", ebody[idx : idx + 8])[0]
                    idx += 8
            epos += 4 + esize

        entries.append({
            "name": fn,
            "compressed_size": actual_c_size,
            "uncompressed_size": actual_u_size,
            "local_header_offset": actual_offset,
            "compression_method": comp_m,
        })
        pos += 46 + fn_len + extra_len + comm_len

    logger.info("Found %d file entries in remote data_all.zip", len(entries))
    return entries


def sample_first_day_events(
    entry: Dict[str, Any],
    max_decompressed_bytes: int = 1048576,  # 1 MB chunk for schema verification
    url: str = ZENODO_DATA_ALL_URL,
) -> List[Dict[str, Any]]:
    """Download the start of the compressed stream for one day and decompress events."""
    l_offset = entry["local_header_offset"]
    # Read local header to get filename and extra field length
    l_hdr = fetch_range(url, l_offset, l_offset + 64)
    if not l_hdr.startswith(b"PK\x03\x04"):
        raise ValueError("Invalid local zip header signature")

    fn_len, extra_len = struct.unpack("<HH", l_hdr[26:30])
    data_start = l_offset + 30 + fn_len + extra_len

    # Fetch initial 512 KB of compressed deflate stream
    fetch_chunk = min(entry["compressed_size"], 524288)
    compressed_bytes = fetch_range(url, data_start, data_start + fetch_chunk - 1)

    # Decompress zip layer using raw DEFLATE (-zlib.MAX_WBITS)
    dobj = zlib.decompressobj(-zlib.MAX_WBITS)
    try:
        decompressed_zip = dobj.decompress(compressed_bytes)
    except Exception as e:
        logger.error("ZIP decompression failed: %s", e)
        return []

    # If the file is .json.gz, decompress gzip layer
    raw_text = ""
    if entry["name"].endswith(".gz"):
        try:
            # Try decompressing gzip stream
            dobj_gz = zlib.decompressobj(zlib.MAX_WBITS | 16)
            decompressed_gz = dobj_gz.decompress(decompressed_zip, max_decompressed_bytes)
            raw_text = decompressed_gz.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning("Gzip decompress failed or partial: %s", e)
            raw_text = decompressed_zip.decode("utf-8", errors="replace")
    else:
        raw_text = decompressed_zip.decode("utf-8", errors="replace")

    lines = raw_text.splitlines()
    events = []
    # Drop first and last lines if partial
    valid_lines = lines[1:-1] if len(lines) > 2 else lines

    for line in valid_lines:
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
            if isinstance(ev, dict):
                events.append(ev)
        except Exception:
            continue

    logger.info("Parsed %d valid dictionary event records from %s", len(events), entry["name"])
    return events


def verify_event_schema(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Inspects present fields in extracted events and verifies REQUIRED_EVENT_FIELDS."""
    all_keys = set()
    for ev in events:
        if isinstance(ev, dict):
            all_keys.update(ev.keys())

    missing = [f for f in REQUIRED_EVENT_FIELDS if f not in all_keys]
    present = [f for f in REQUIRED_EVENT_FIELDS if f in all_keys]

    return {
        "status": "VERIFIED" if not missing else "PARTIAL",
        "sample_events_count": len(events),
        "total_unique_fields_found": len(all_keys),
        "required_fields_present": sorted(present),
        "required_fields_missing": sorted(missing),
        "all_fields_found": sorted(list(all_keys)),
    }


def run_s3_part2_check(output_path: str = "results/s3_event_schema.json") -> Dict[str, Any]:
    """Executes S3 Part 2 investigation and writes verification report."""
    entries = list_zip_entries()
    if not entries:
        raise RuntimeError("No entries found in data_all.zip")

    # Pick first day entry (e.g. 2025-06-27 or similar)
    first_entry = entries[0]
    logger.info("Sampling event data from entry: %s", first_entry["name"])

    events = sample_first_day_events(first_entry)
    schema_report = verify_event_schema(events)

    result = {
        "spike": "S3 Part 2 (Event-level Archive Verification)",
        "archive_url": ZENODO_DATA_ALL_URL,
        "archive_total_size_bytes": TOTAL_FILE_SIZE,
        "total_days_in_archive": len(entries),
        "day_files": [e["name"] for e in entries],
        "sampled_file": first_entry["name"],
        "schema_verification": schema_report,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    logger.info("Saved S3 Part 2 schema verification to %s", output_path)
    return result


if __name__ == "__main__":
    run_s3_part2_check()
