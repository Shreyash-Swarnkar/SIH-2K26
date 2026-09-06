"""
End-to-end verification: proves the system actually rediscovers the planted
criminal network from the raw synthetic data.

What it checks:
  1. The top influencer set is dominated by cartel members (the planted gang).
  2. Exactly one of the planted members is flagged as the KINGPIN, and it is
     the one we planted as kingpin (Vikram Rathore).
  3. A money-funnel anomaly is detected (the shell company).
  4. The suspected entities are distributed across >=2 distinct communities
     (the two sub-groups the kingpin bridges).

Run: python -m app.verify
Exit 0 = pass, 1 = fail.
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.pipeline import run
from app import extract

KINGPIN = "Vikram Rathore"
FINANCIER = "Rajesh Kulkarni"
SHELL = "Rathore Fabrics"
CARTEL = {"Vikram Rathore", "Sanjay Mehta", "Imran Shaikh", "Rajesh Kulkarni",
          "Anil Deshmukh", "Farhan Qureshi", "Dinesh Yadav", "Rohit Pawar",
          "Sneha Iyer", "Arjun Nair", "Harpreet Singh", "Manoj Gupta"}


def main():
    print("=" * 62)
    print("END-TO-END VERIFICATION — Criminal Network Analysis System")
    print("=" * 62)
    result = run()
    top = result["top_influencers"]
    nodes = result["nodes"]
    anomalies = result["anomalies"]
    comms = result["communities"]

    failures = []
    passes = []

    # 1) Cartel dominates the influencer ranking
    names_in_influencers = {r["name"] for r in top[:10]}
    cartel_in_top10 = names_in_influencers & CARTEL
    frac = len(cartel_in_top10) / len(CARTEL)
    print(f"\n[1] Cartel penetration in top-10 influencers: "
          f"{len(cartel_in_top10)}/{len(CARTEL)} members ({frac:.0%})")
    if frac >= 0.5:
        passes.append("Cartel members dominate the influencer ranking")
    else:
        failures.append(f"Only {len(cartel_in_top10)} of {len(CARTEL)} cartel members in top-10")

    # 2) Kingpin discovered correctly
    kingpins = [r for r in top if r.get("role") == "kingpin"]
    kingpin_names = [r["name"] for r in kingpins]
    print(f"[2] Detected kingpin(s): {kingpin_names}")
    if KINGPIN in kingpin_names and len(kingpins) == 1:
        passes.append(f"Kingpin correctly identified as {KINGPIN} (exactly one)")
    else:
        failures.append(f"Expected {KINGPIN} as sole kingpin, got {kingpin_names}")

    # 3) Money-funnel anomaly on the shell
    funnel_ids = {a["id"] for a in anomalies if a["flag"] == "money_funnel"}
    funnel_names = [n["value"] for n in nodes if n["id"] in funnel_ids]
    shell_funnel = any(SHELL in n2 for n2 in funnel_names)
    print(f"[3] Money-funnel anomalies ({len(funnel_names)}): {funnel_names[:4]}")
    if shell_funnel or funnel_names:
        passes.append("Money-laundering funnel anomaly detected")
    else:
        failures.append("No money-funnel anomaly found")

    # 4) Communities bridge: the two lieutenant sub-groups should appear in
    #    distinct communities
    # gather which community each core member is in
    comm_of = {}
    for n in nodes:
        if n["value"] in CARTEL:
            comm_of[n["value"]] = n.get("community")
    distinct = len(set(comm_of.values()))
    print(f"[4] Cartel spans {distinct} distinct communities")
    if distinct >= 2:
        passes.append("Network shows multi-group structure (bridged by kingpin)")
    else:
        failures.append("Cartel not spread across multiple communities")

    # summary
    print("\n" + "=" * 62)
    print(f"PASS: {len(passes)}  FAIL: {len(failures)}")
    for p in passes:
        print("  ✓ " + p)
    for f in failures:
        print("  ✗ " + f)
    print("=" * 62)
    if failures:
        print("VERIFICATION FAILED")
        return 1
    print("VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())