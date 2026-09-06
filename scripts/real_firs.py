#!/usr/bin/env python
"""
Convert the real ICDAR FIR annotations (FIR_details.json) into plain-text
FIR documents that the pipeline's extractor can read.

Source: https://github.com/LegalDocumentProcessing/FIR_Dataset_ICDAR2023
  Real FIR records photographed at police stations across West Bengal,
  Rajasthan, Sikkim, Tripura and Nagaland.
  Annotation categories: 0=police station, 1=year, 2=statutes, 3=complainant.

Output: data/real/firs/<ps-slug>__<n>.txt  (one narrative FIR per document)
"""
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "data", "real", "fir_dataset", "FIR_details.json")
OUT = os.path.join(HERE, "..", "data", "real", "firs")


def slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "fir"


def main():
    recs = json.load(open(SRC, encoding="utf-8"))
    per_fir: dict[str, dict] = defaultdict(lambda: {0: [], 1: [], 2: [], 3: []})
    for r in recs:
        per_fir[r["image_name"]][r["category_id"]].append(r["text"])

    os.makedirs(OUT, exist_ok=True)
    written = 0
    for img, cats in per_fir.items():
        ps = " ".join(cats[0]).strip() or "Police Station"
        year = cats[1][0] if cats[1] else ""
        statutes = " ".join(cats[2]).strip() or "I.P.C."
        complainants = [t.strip() for t in cats[3] if t.strip()]
        if not complainants:
            continue
        filename = f"{slug(ps)}__{written+1:03d}.txt"
        body = (
            f"FIR incident report at {ps}, {year}.\n"
            f"Complainant {complainants[0]} filed a report before the officer-in-charge "
            f"stating that an offence was committed. "
            f"Investigation initiated under {statutes}.\n"
            f"Case details recorded at {ps} police station."
        )
        with open(os.path.join(OUT, filename), "w", encoding="utf-8") as f:
            f.write(body)
        written += 1

    print(f"[real-firs] wrote {written} real FIR documents to {os.path.relpath(OUT, HERE)}")


if __name__ == "__main__":
    main()