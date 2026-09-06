#!/usr/bin/env python
"""
Run the pipeline over REAL police FIR data (data/real/firs) and write a
separate results file so the real-data analysis never clobbers the synthetic
demo output.

Real source: ICDAR FIR dataset — FIR documents photographed at police stations
in West Bengal, Rajasthan, Sikkim, Tripura and Nagaland, annotations extracted
by scripts/real_firs.py into plain-text documents.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extract import run_pipeline
from app.graph_analytics import analyze

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_DIR = os.path.join(ROOT, "data", "real")
OUT = os.path.join(ROOT, "data", "results", "results_real.json")


def main():
    t0 = time.time()
    extracted = run_pipeline(
        fir_dir=os.path.join(REAL_DIR, "firs"),
        cdr_dir=os.path.join(REAL_DIR, "cdrs"),   # absent -> skipped
        bank_dir=os.path.join(REAL_DIR, "banking"),  # absent -> skipped
    )
    analytics = analyze(extracted["entities"], extracted["edges"])

    data = {**analytics, "entities": extracted["entities"], "relations": extracted["edges"]}
    with open(OUT, "w", encoding="utf-8") as f:
        import json; json.dump(data, f, indent=2, default=str)

    n = analytics["stats"]
    print(f"[real-data] {n['n_nodes']} nodes, {n['n_edges']} edges, "
          f"{n['n_communities']} communities, {len(analytics['anomalies'])} anomalies")
    print(f"[real-data] results -> {OUT}")
    print("\n=== TOP (REAL FIRSTS DATA) ===")
    for i, inf in enumerate(analytics["top_influencers"][:12], 1):
        print(f"  {i:2d}. {inf['name'][:35]:<35s} [{inf.get('role','?'):<10s}] threat={inf['threat']:.4f}")
    print("\n=== ANOMALIES (real) ===")
    for a in analytics["anomalies"][:10]:
        print(f"  [{a['flag']}] {a['id']}: {a['note']}")


if __name__ == "__main__":
    main()