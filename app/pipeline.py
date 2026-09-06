"""
Pipeline runner: ties data -> extraction -> graph analytics -> JSON output.

Run: python -m app.pipeline
Loads synthetic data, runs entity extraction, builds graph, runs analytics,
writes results.json. Also serves as the backbone behind the FastAPI endpoint.
"""
from __future__ import annotations
import os, json, sys, time

# Allow running from project root: python -m app.pipeline
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.extract import run_pipeline
from app.graph_analytics import analyze


DATA_DIR = os.path.join(ROOT, "data", "synthetic")
OUT_DIR  = os.path.join(ROOT, "data", "results")
os.makedirs(OUT_DIR, exist_ok=True)


def run(data_dir: str = DATA_DIR) -> dict:
    fir_dir  = os.path.join(data_dir, "firs")
    cdr_dir  = os.path.join(data_dir, "cdrs")
    bank_dir = os.path.join(data_dir, "banking")

    print(f"[*] Extraction from: {data_dir}")
    t0 = time.time()
    extracted = run_pipeline(fir_dir, cdr_dir, bank_dir)
    t1 = time.time()
    n_ent = len(extracted["entities"])
    n_rel = len(extracted["edges"])
    print(f"    Extracted {n_ent} entities, {n_rel} relations in {t1-t0:.1f}s")

    print("[*] Graph analytics...")
    t2 = time.time()
    analytics = analyze(extracted["entities"], extracted["edges"])
    t3 = time.time()
    print(f"    {analytics['stats']['n_nodes']} nodes, "
          f"{analytics['stats']['n_edges']} edges, "
          f"{analytics['stats']['n_communities']} communities in {t3-t2:.1f}s")

    # Save
    out = {**analytics,
           "entities": extracted["entities"],
           "relations": extracted["edges"]}
    path = os.path.join(OUT_DIR, "results.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"[*] Results -> {path}")

    # Quick summary
    print("\n=== TOP INFLUENCERS ===")
    for i, inf in enumerate(analytics["top_influencers"][:12], 1):
        print(f"  {i:2d}. {inf['name']:<35s} [{inf.get('role','?'):<10s}] "
              f"threat={inf['threat']:.4f}  ({inf['type']})")

    print(f"\n=== COMMUNITIES ({len(analytics['communities'])}) ===")
    for c in analytics["communities"][:5]:
        print(f"  Community {c['community']}: {c['size']} nodes, "
              f"threat={c['threat']:.3f}")

    print(f"\n=== ANOMALIES ({len(analytics['anomalies'])}) ===")
    for a in analytics["anomalies"][:10]:
        print(f"  [{a['flag']}] {a['id']}: {a['note']}")

    return out


if __name__ == "__main__":
    run()
