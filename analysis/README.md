# Analysis Environment & Pipelines

## Python Runtime
- **Python Version**: `3.12.10` (Windows x86-64)
- **Virtual Environment**: `.venv` (created via `python -m venv .venv`)
- **Pinned Dependencies**: `duckdb==2.0.0`, `pytest==9.2.0` (in `requirements.txt`)

## Setup Instructions
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

To run test suites:
```powershell
.\.venv\Scripts\python.exe -m pytest analysis/ -v
```

---

## Dataset Download Instructions (Human Task for Spike S3)

Per `SAFETY.md` and `DATA.md`, download **ONLY** `session_aggregation.jsonl.gz`.
**DO NOT** download `transferred_files.zip`.

### 1. Download `session_aggregation.jsonl.gz`
- **Record**: Zenodo Record `21260400` (https://zenodo.org/records/21260400)
- **Direct Content URL**: `https://zenodo.org/api/records/21260400/files/session_aggregation.jsonl.gz/content`
- **Target Path**: `data/session_aggregation.jsonl.gz`
- **Expected Size**: ~1.3 GB compressed
- **Expected MD5**: `1f3897650fb420c97c14ff452398c3f8`

#### Option A: PowerShell Download
```powershell
Invoke-WebRequest -Uri "https://zenodo.org/api/records/21260400/files/session_aggregation.jsonl.gz/content" -OutFile "data\session_aggregation.jsonl.gz"
```

#### Option B: curl Download
```bash
curl -L -o data/session_aggregation.jsonl.gz "https://zenodo.org/api/records/21260400/files/session_aggregation.jsonl.gz/content"
```

#### Option C: Web Browser
1. Navigate to https://zenodo.org/records/21260400
2. Locate `session_aggregation.jsonl.gz` (1.3 GB) in the Files list and click Download.
3. Save the downloaded file directly into `data/session_aggregation.jsonl.gz`.

---

### 2. Verify Checksum
Run the chunked MD5 streaming verifier:
```powershell
.\.venv\Scripts\python.exe analysis/verify_download.py data/session_aggregation.jsonl.gz 1f3897650fb420c97c14ff452398c3f8
```
- Exit code `0` and output `MATCH: ...` confirms integrity.
- Exit code `1` and output `MISMATCH: ...` indicates a corrupted or incomplete download; re-download if mismatched.
