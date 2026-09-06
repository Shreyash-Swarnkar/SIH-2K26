"""
Real-world data ingestion.

The demo runs on the synthetic generator, but the system is built to accept
real files too. Drop files into a directory and call `run_pipeline` with the
right subfolders, OR add handlers here for your source's layout.

Expected layouts (matching app/extract.parse_*):
  firs/     — one .txt per FIR/report (any narration; entities are extracted
              with spaCy NER + custom regex)
  cdrs/     — CSV: caller, receiver, call_start_time, duration_sec [, cell_id]
  banking/  — CSV: from_account, to_account, amount, type, description

This module provides:
  * ingest_fir_bundle(dir)   — read every .txt in a folder as an FIR doc.
  * ingest_standard_cdrs(x)  — map many common CDR column names.
  * ingest_standard_banks(x) — map many common transaction column names.
"""
import csv
import os
import re


# ---- FIR / unstructured text -------------------------------------------------
def ingest_fir_bundle(fir_dir: str) -> list[str]:
    """Return the raw text of every .txt file under fir_dir (recursively)."""
    docs = []
    if not os.path.isdir(fir_dir):
        return docs
    for root, _d, files in os.walk(fir_dir):
        for fn in sorted(files):
            if fn.lower().endswith(".txt"):
                with open(os.path.join(root, fn), encoding="utf-8", errors="ignore") as f:
                    docs.append(f.read())
    return docs


# ---- CDR column-name aliases -------------------------------------------------
_CDR_ALIASES = {
    "caller": ("caller", "a_party", "calling_no", "src", "source", "mobile_no", "from_no", "ans_call"),
    "receiver": ("receiver", "b_party", "called_no", "dst", "target", "to_no", "dialed_no"),
    "start": ("call_start_time", "start_time", "timestamp", "datetime", "date", "time", "call_time"),
    "duration": ("duration_sec", "duration", "call_duration", "dur", "duration_seconds"),
}
_CDR_HEADER_RE = {k: [re.compile(a, re.I) for a in v] for k, v in _CDR_ALIASES.items()}

def _match_header(header: list[str], aliases):
    """Return index of first header column matching any alias (str or Pattern)."""
    for i, col in enumerate(header):
        for a in aliases:
            if hasattr(a, "search"):
                if a.search(col):
                    return i
            elif a.lower() in col.lower():
                return i
    return -1


def ingest_standard_cdrs(path: str):
    """Return list of dicts {caller, receiver, start, duration} for a CSV with
    conventional column names."""
    out = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        rd = csv.reader(f)
        header = next(rd, None)
        if not header:
            return out
        ci = {k: _match_header(header, v) for k, v in zip(_CDR_ALIASES, _CDR_ALIASES.values())}
        for row in rd:
            rec = {}
            for k, idx in ci.items():
                if idx >= 0 and idx < len(row):
                    rec[k] = row[idx].strip()
            out.append(rec)
    return out


# ---- banking column-name aliases ---------------------------------------------
_BANK_ALIASES = {
    "from": ("from_account", "src_account", "sender", "payer", "from", "debit_account"),
    "to": ("to_account", "dst_account", "beneficiary", "payee", "to", "credit_account"),
    "amount": ("amount", "amt", "value", "usd", "amount_usd"),
    "date": ("date", "datetime", "timestamp", "txn_date", "tran_date"),
}
_BANK_HEADER_RE = {k: [re.compile(a, re.I) for a in v] for k, v in _BANK_ALIASES.items()}

def ingest_standard_banks(path: str):
    """Return list of dicts {from_account, to_account, amount, date}."""
    out = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        rd = csv.reader(f)
        header = next(rd, None)
        if not header:
            return out
        ci = {k: _match_header(header, v) for k, v in zip(_BANK_ALIASES, _BANK_ALIASES.values())}
        for row in rd:
            rec = {}
            for k, idx in ci.items():
                if idx >= 0 and idx < len(row):
                    rec[k] = row[idx].strip()
            out.append(rec)
    return out