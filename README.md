# 🕵️ AI-Powered Criminal Network Analysis System

> **SIH 2026** submission — automatically uncovers hidden criminal networks from fragmented FIRs, call detail records (CDRs), and financial transactions.

## What it does

Ingests real/synthetic crime data, uses **NLP entity extraction**, builds a **relationship graph**, runs **graph analytics** (centrality, community detection, anomaly detection), and **classifies roles** (kingpin / financier / lieutenant / associate). Results surface on an **interactive network dashboard**.

The system *discovers* hidden structure — in our demo data it independently finds **Vikram Rathore as the kingpin** and **Rajesh Kulkarni as the money launderer**, despite the connections being scattered across 75+ separate documents and noisy records.

## Architecture

```
data/synthetic/   ← generated FIRs, CDRs, banking transactions (hides a cartel)
   └ firs/  cdrs/  banking/
app/
   gen_data.py        ← synthetic data generator (embeds a hidden criminal network)
   extract.py         ← NLP: NER + regex entity extraction, cross-source entity resolution
   graph_analytics.py ← NetworkX: centrality, communities, anomalies, role classifier
   pipeline.py        ← orchestrates extraction → analytics → results.json
   verify.py          ← end-to-end self-test (asserts the gang + kingpin are rediscovered)
   api.py             ← FastAPI backend
   dashboard.html     ← interactive network visualization (Cytoscape.js)
run.py               ← one-command launcher
```

## Setup

```bash
# Python 3.11 + uv (pip absent on this machine)
uv venv --python 3.11 .venv
VIRTUAL_ENV=.venv uv pip install -r requirements.txt
# optionally install the spaCy model (falls back to regex NER if unavailable):
VIRTUAL_ENV=.venv uv pip install spacy
.venv/Scripts/python -m spacy download en_core_web_sm
```

> **Windows note:** if spaCy's compiled extensions fail with `DLL load failed ... msvcp140.dll`, install the
> **Microsoft Visual C++ Redistributable (x64)** and restart the shell. The system runs fine without spaCy
> via a built-in regex entity extractor.

## Run (demo)

```bash
.venv/Scripts/python run.py all      # regenerate data, run pipeline, verify
.venv/Scripts/python run.py serve    # start dashboard at http://127.0.0.1:8000
```

Open `http://127.0.0.1:8000/ui` — the dashboard shows the network graph, ranked influencers w/ roles, and anomalies. Click **Re-analyze dataset** to re-run on demand, or use the **dataset selector** to switch between the synthetic demo and the real police-FIR analysis.

Individual steps: `python run.py data` / `pipeline` / `verify`.

## Real police data (FIRs)

The system also runs on **real FIR records**. We pull the published
[ICDAR 2023 FIR dataset](https://github.com/LegalDocumentProcessing/FIR_Dataset_ICDAR2023) —
FIR documents photographed at police stations across West Bengal, Rajasthan,
Sikkim, Tripura and Nagaland, with 2,447 annotated fields (police station, year,
statutes, complainant).

```bash
.venv/Scripts/python scripts/real_firs.py   # annotations -> data/real/firs/*.txt (512 FIRs)
.venv/Scripts/python scripts/run_real.py    # run the full pipeline on real FIRs
# -> data/results/results_real.json; view via dashboard selector "Real police FIRs"
```

The NLP layer (spaCy NER + domain regex + a hardened person-plausibility guard
that rejects statute strings, station names and titles) extracts only human
actors from the real docs — so the top influencers you get back are actual
named people, not "420/406 Ipc" or "Baguiati Ps".

## How the analytics find the "who's who"

| Role | Signal |
|------|--------|
| **kingpin** | articulation point (bridge) **and** net money *receiver* — controls the flow |
| **financier** | money *sender* at consolidation scale — the launderer |
| **lieutenant** | bridge with high centrality |
| **associate** | moderately central node |

Scoring blends **betweenness + eigenvector (structure) + strength/degree (activity)**, normalized per dimension so money flow can't drown the other signals.

## Roadmap (future work for a fuller submission)

- Social-media ingestion & sentiment analysis
- Temporal link analysis (when did edges form)
- Neo4j for scale + queryable subgraphs
- Investigative agent: natural-language questions over the graph"# SIH-2K26" 
