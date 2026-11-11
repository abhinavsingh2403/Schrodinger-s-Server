# HANDOFF.md: Model Handoff & Progress Ledger

## STATUS
- Current Task: G2 (Complete)
- Awaiting: Human download of `data/session_aggregation.jsonl.gz` and MD5 verification.
- Next Model Task: G3 (S3 base-rate script + tests on verified dataset).

---

## DONE
1. Created `analysis/verify_download.py` which streams files in chunks to compute MD5 digest, prints `MATCH` or `MISMATCH` with computed and expected hashes, and exits non-zero on mismatch or missing file.
2. Created `analysis/test_verify_download.py` providing unit tests for match, mismatch, and missing file error handling.
3. Created virtual environment `.venv` and installed pinned dependencies `duckdb==2.0.0` and `pytest==9.2.0`.
4. Verified tests with pytest: all 3 unit tests passed cleanly.
5. Resolved exact direct content download URL from Zenodo API (`https://zenodo.org/api/records/21260400/files/session_aggregation.jsonl.gz/content`).
6. Updated `analysis/README.md` documenting exact PowerShell, curl, and browser download commands, target path `data/session_aggregation.jsonl.gz`, expected MD5 `1f3897650fb420c97c14ff452398c3f8`, and verification invocation.
7. Added `.pytest_cache/` to `.gitignore`.

---

## FILES
- `.gitignore` (modified)
- `analysis/README.md` (modified)
- `analysis/verify_download.py` (created)
- `analysis/test_verify_download.py` (created)
- `HANDOFF.md` (modified)

---

## COMMANDS AND OUTCOMES
1. Zenodo API check:
   ```powershell
   > python -c "import urllib.request, json; r = urllib.request.urlopen('https://zenodo.org/api/records/21260400'); data = json.loads(r.read()); print('\n'.join(f['key'] + ' -> ' + f['links']['self'] for f in data.get('files', [])))"
   session_aggregation.jsonl.gz -> https://zenodo.org/api/records/21260400/files/session_aggregation.jsonl.gz/content
   ```
2. Virtualenv setup & installation:
   ```powershell
   > python -m venv .venv
   > .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   Successfully installed colorama-0.4.6 duckdb-2.0.0 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.2.0
   ```
3. Pytest test run:
   ```powershell
   > .\.venv\Scripts\python.exe -m pytest analysis/test_verify_download.py -v
   ============================= test session starts =============================
   platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\abhip\OneDrive\Documents\mini project\.venv\Scripts\python.exe
   cachedir: .pytest_cache
   rootdir: C:\Users\abhip\OneDrive\Documents\mini project
   collecting ... collected 3 items

   analysis/test_verify_download.py::test_compute_md5_and_verify_match PASSED [ 33%]
   analysis/test_verify_download.py::test_verify_mismatch PASSED            [ 66%]
   analysis/test_verify_download.py::test_verify_missing_file PASSED        [100%]

   ============================== 3 passed in 0.04s ==============================
   ```

---

## TODO(verify)
*(None for Task G2; direct URL confirmed against Zenodo API).*

---

## QUESTIONS FOR OPUS
*(None for Task G2).*

---

## QUESTIONS FOR HUMAN
Please execute the download of `session_aggregation.jsonl.gz` into `data/` and verify its MD5 before Task G3 is executed:
```powershell
# 1. Download (~1.3 GB)
Invoke-WebRequest -Uri "https://zenodo.org/api/records/21260400/files/session_aggregation.jsonl.gz/content" -OutFile "data\session_aggregation.jsonl.gz"

# 2. Verify
.\.venv\Scripts\python.exe analysis/verify_download.py data/session_aggregation.jsonl.gz 1f3897650fb420c97c14ff452398c3f8
```
Let the agent know once the verification outputs `MATCH`.
