# 🕵️ AI-Powered Criminal Network Analysis System — Team Handbook

> **SIH 2026 · Team Project Guide**
> Everything you need to understand the project, demo it, and explain the code under pressure.
> Read this top to bottom once; keep it open during practice runs.

---

## 1. What the project is (one paragraph)

Modern criminals operate as **networks** — a kingpin, lieutenants, a money launderer, a logistics guy, and associates who never touch the kingpin directly. Police data about them (FIRs, call records, bank transactions) is **fragmented, unstructured, and scattered across many systems**, so human analysts often miss the hidden links. Our system **automatically turns that mess into one connected graph** using NLP + graph analytics, then answers the question investigators actually care about: *"Who is the kingpin, who is the money-launderer, and which gang are they part of?"*

The demo **proves** this works: we feed it raw noise-filled files and it independently re-discovers the planted criminal network — including flagging **Vikram Rathore as the kingpin** and **Rajesh Kulkarni as the launderer** — even though their connections are hidden across 75+ separate documents with burner phones, a shell company, and ~60% innocuous noise.

---

## 2. The problem statement (SIH)

**Objective:** Build an AI system that analyzes large volumes of criminal and intelligence data to uncover hidden networks and relationships among individuals, organizations, locations, and events.

The system must:
- Collect & process data from multiple sources
- Extract entities (people, locations, vehicles, phone numbers, organizations)
- Build relationship maps between entities
- Identify key/influential individuals in criminal networks
- Detect suspicious patterns & unusual activity
- Provide visual and analytical insight to investigators

**Our answer:** a working prototype (FastAPI + interactive web dashboard) that does all of the above end-to-end.

---

## 3. High-level architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                                 │
│   FIRs (.txt)   │   CDRs (calls)  │   Bank txns   │  Social/…    │
└────────┬────────────┬────────────────┬───────────┘
         ▼            ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│  EXTRACTION  (app/extract.py)  —  NLP core                      │
│   · spaCy NER + domain regex → people, orgs, locs, phones,      │
│     vehicles, amounts, FIR numbers                               │
│   · Cross-source entity resolution (same person across files)    │
│   · co-occurrence + call + money edges with weight & evidence    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  GRAPH ANALYTICS  (app/graph_analytics.py)                      │
│   · NetworkX graph + Louvain communities (gangs)                 │
│   · Centrality → who matters (kingpin / fixer)                   │
│   · Anomaly rules → money-funnel, high-traffic, bridge node      │
│   · Role classifier → kingpin · financier · lieutenant · assoc   │
│   · Composite threat score                                       │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  RESULTS.JSON  →  FastAPI  (app/api.py)  →  Dashboard (HTML)     │
│     interactive network graph, ranked influencers, anomalies     │
└─────────────────────────────────────────────────────────────────┘
```

**The one-sentence version for judging:** *"Raw fragmented documents → NLP entity extraction → graph analytics → 'this person is the kingpin'."*

---

## 4. The key idea: a demo that re-discovers a hidden network

The heart of the demo is **verification**: we didn't just build software that produces output — we built a dataset that **hides a real criminal structure** and a self-test that checks the system finds it.

**The hidden network we plant** (in `scripts/gen_data.py`):
- **1 kingpin** — Vikram Rathore. Deliberately "quiet": very few direct calls, works through intermediaries, owns the shell company.
- **2 lieutenants** — Sanjay Mehta, Imran Shaikh (high call volume, bridge the two sub-groups).
- **1 money launderer** — Rajesh Kulkarni; handles and funnels all proceeds.
- **1 logistics** node — Anil Deshmukh.
- **1 communicator** — Farhan Qureshi (encrypted-channel style call pattern).
- **~6 associates** scattered across cities (Delhi, Kochi, Ludhiana, Mumbai…).
- A **shell company** "Rathore Fabrics Pvt Ltd" used for laundering.
- **~60% noise** — random innocent citizens and businesses, so the signal is genuinely buried.

**The obfuscation we throw at the system** (to make it realistic):
- Burner phone swaps, vehicles shared within the ring, recurring disguised "settlement" transactions, connections scattered across many different documents.

`app/verify.py` then asserts the system **rediscovers** all this from raw files:
1. Cartel members dominate the top-10 influencer ranking (≥50%).
2. Exactly **one** kingpin is found and it is **Vikram Rathore**.
3. A **money-funnel** anomaly is flagged (the shell).
4. The cartel spans **≥2 communities** (the two sub-groups the kingpin bridges).

> **Memorize this.** When a judge asks "does it actually work?", run the verify step and show the passes. It is our strongest proof.

---

## 5. Role of each code file (the map)

| File | What it does | Run it with |
|---|---|---|
| `run.py` | One-command launcher (data / pipeline / verify / serve / all) | `python run.py all` |
| `scripts/gen_data.py` | Generates the synthetic noisy dataset that *hides* the network | `python run.py data` |
| `app/extract.py` | **NLP core** — entities + edges from text/CDRs/bank files | (part of pipeline) |
| `app/graph_analytics.py` | **Graph analytics** — communities, centrality, anomalies, threat, roles | (part of pipeline) |
| `app/pipeline.py` | Orchestrates extract → analytics → `results.json` | `python run.py pipeline` |
| `app/verify.py` | End-to-end self-test (seeks the planted gang + kingpin) | `python run.py verify` |
| `app/api.py` | **FastAPI backend** — serves dashboard + `/analyze`, `/results` endpoints | `python run.py serve` |
| `app/dashboard.html` | **Interactive network visualisation** (Cytoscape.js) | (served by api.py) |
| `app/ingest.py` | Adapters for *real-world* file formats (column-name aliases) | (utility) |
| `scripts/real_firs.py` | Downloads/parses the real ICDAR 2023 FIR dataset | `python scripts/real_firs.py` |
| `scripts/run_real.py` | Runs the full pipeline on **real police FIRs** | `python scripts/run_real.py` |
| `data/` | Generated datasets (`synthetic/`) + outputs (`results.json`) | — |
| `docs/DEMO_SCRIPT.md` | Step-by-step presentation script | — |

---

## 6. The data model (entities & relations)

**Entities** (typed nodes) — `extract.py`:
- `PERSON`, `ORG`, `LOC`, `PHONE`, `VEHICLE`, `DATE`, `AMOUNT`, `FIR`, `ACCOUNT`.

**Relations** (weighted edges), each carrying `kinds` + `evidence` (which source file/text):
- **`co-occur`** — two entity types appear in the same document (the workhorse "they're connected" signal).
- **`call`** — phone-to-phone calls from CDRs.
- **`money`** — account→account transfers; weight scales with amount, direction preserved (this powers laundering detection).

**Identity resolution** (`extract.py` → `pipeline.py`):
- A phone/vehicle found near a person's name in the same document is **attached to that person** (proximity match).
- After extraction, phone/vehicle/account nodes **merge into their owning person**, re-pointing every edge onto the person.
- This is how "Rajesh Kulkarni's 98220-77665 paid ₹40L to Rathore Fabrics" becomes a **person-to-person/org link** the analyst can read.

---

## 7. The analytics: how we find the "who's who"

The investigator's core question is *who*. We answer with a blend, deliberately balanced so money flow can't drown out the other signals.

**Centrality measures** (`add_centrality`):
- **Betweenness** → who acts as a *bridge* between parts of the network = the fixer/coordinator.
- **Eigenvector** → who is connected to *other important people* = the quiet controller (kingpins are deliberately low-profile but everyone points at them).
- **Strength / degree** → raw activity volume (calls, edges, money moved).

**Threat score** (composite, normalized 0→1):
```
threat = 0.30·betweenness + 0.25·eigenvector + 0.20·strength + 0.25·degree  (+ small boost per anomaly flag)
```

**Community detection:** Louvain (`python-louvain`) groups nodes into gangs. Fallback = connected components if the library is missing.

**Anomaly rules** (`detect_anomalies`) — human-readable flags an officer can act on:
- `money_funnel` — an account sends >55% of its value to a single recipient (the shell).
- `high_traffic` — a node with many contacts + heavy interaction volume.
- `bridge_node` — an articulation point; removing it fragments the network.

**Role classification** — the "who's who" answer:
| Role | Signal |
|---|---|
| **kingpin** | a *bridge* person who is also a **net money receiver** (money flows *to* them) |
| **financier / launderer** | a money *sender* at a scale that is a clear outlier (≥3× the median outflow), or a money-funnel account |
| **lieutenant** | bridge with high centrality (but not the top controller) |
| **associate** | moderately central |
| **account / node** | everything else |

One guard ensures a **single** top controller is surfaced: among money-sink bridges, the highest-threat one is crowned the one-and-only kingpin.

---

## 8. The dashboard

Served at `http://127.0.0.1:8000/ui`, built with **Cytoscape.js** (served **locally**, works offline — no CDN dependency, great for a demo venue with no internet).

What the investigator sees:
- The **full network graph** — nodes colored/typed, edges weighted.
- **Ranked influencers** with `role` + `threat` score.
- **Communities** (the gangs) ranked by aggregate threat.
- **Anomalies** with plain-English notes.
- A **dataset selector** to switch between the synthetic demo and the **real police FIRs**.
- A **"Re-analyze dataset"** button to re-run the pipeline live on demand.

---

## 9. The real-data angle (why this isn't fake)

The system doesn't only work on our synthetic demo — it also runs on **real Indian police FIRs** from the **ICDAR 2023 FIR Dataset** (photographed FIRs from West Bengal, Rajasthan, Sikkim, Tripura, Nagaland; 2,447 annotated fields).

Through `scripts/real_firs.py` + `scripts/run_real.py`, we convert the annotations → `data/real/firs/*.txt` (512 FIRs) and run the same pipeline. The NLP layer includes a hardened **person-plausibility guard** (see below) so the top influencers returned are *actual named people* — not OCR errors like "420/406 Ipc" or "Baguiati Ps".

---

## 10. Programming explanation (the deep dive)

Everything below is Python 3.11, managed with `uv`. Here's exactly what each core module does under the hood.

### 10.1 `app/extract.py` — the NLP core

**Two extraction engines working together:**

1. **spaCy NER** (`en_core_web_sm`) finds `PERSON`, `ORG`, `LOC/GPE/FAC`, `DATE` spans. It's fast and general but *noisy* on crime text — it calls car makes like "Maruti Swift" a PERSON and statute strings like "420/406 Ipc" a person. So every PERSON span must pass **`_plausible_person()`** — a guard that rejects:
   - Non-alphabetic-leading tokens (`420/406 Ipc`)
   - Legal/station words anywhere (`ipc`, `ps`, `section`, `constable`…)
   - Known non-person words, vehicle makes, and geographic suffixes (`Nagar`, `Estate`…)

2. **Domain regex** overlays catch the high-signal artifacts spaCy is weak on:
   - Indian phone numbers (`PHONE_RE`, e.g. `[987]xxxxxxxxx`)
   - Vehicle registrations (`VEHICLE_RE` — `MH-01-AB-3344`)
   - FIR / case numbers (`FIRNO_RE` → `FIR_502`)
   - Money amounts (`AMOUNT_RE` → `Rs. 40,00,000`)

   There is also a **pure-python person regex** (`extract_persons_regex`) as a fallback when spaCy's compiled extensions can't load (e.g. a missing VC++ runtime on Windows) — so the system **still works without spaCy**, just with less recall.

**The orchestration** — `run_pipeline(fir_dir, cdr_dir, bank_dir)`:
- Reads every FIR `.txt`, runs `extract_from_text`, registers typed entities.
- Within each document, **co-occurrence edges** connect every pair of desugared "linker" entities (PERSON/PHONE/VEHICLE/ORG).
- Updates the **identity map**: a phone/vehicle owned by whichever person's name appears nearest in the same text (proximity).
- Parses CDRs → `call` edges between phone nodes.
- Parses bank files → `money` edges, weight `1.0 + amount/1e6` (capped), direction preserved (`(sender, receiver)`).
- **Merge phase:** re-points every edge landing on a phone/vehicle/account onto its owning person (accounts whose name contains a known person's full name also merge). Then computes **net money flow** per node (`+receiver / −sender`) — the seed signal for laundering.

> **Tip for pitch:** "We don't just throw text into a black box. We run NER, then de-noise it hard so the model can't hallucinate people out of car names, then we resolve 'phon 98220…' to the person who owns it — that's what lets us read a money transfer as a person-to-person/person-to-org relationship."

### 10.2 `app/graph_analytics.py` — turning entities into intelligence

- **`build_graph`** → a `networkx.Graph`. Node attributes carried, edge `weight` summed if duplicates, `kinds` and `evidence` recorded.
- **`add_centrality`** → betweenness (weighted, sampled `k=min(n,200)` for speed), degree, weighted strength, eigenvector (with a safe fallback if it fails to converge).
- **`community_label`** → Louvain partition (`python-louvain`, fixed seed `random_state=42` for reproducibility) or connected-components fallback.
- **`detect_anomalies`** → the three rules above; `bridge_node` uses `nx.articulation_points`.
- **`analyze`** → normalizes each centrality to 0–1 (so money flow can't dominate), blends into the **threat score**, ranks top-25 influencers **excluding pure LOC/VEHICLE**, runs the **role classifier**, ranks communities by aggregate threat, and returns the full `{nodes, edges, top_influencers, communities, anomalies, stats}` that the API + dashboard consume.

> **Why the blend is defensible:** a naive networkx `betweenness` alone would over-rate a low-activity-but-central person and miss the launderer; a pure money-flow measure would be dominated by one big transfer. The 30/25/20/25 split, each normalized, is our explicit, explainable design choice — perfect to quote when a judge asks "how do you avoid false winners?"

### 10.3 `app/pipeline.py` — the glue

- Computes `ROOT` and both `data/synthetic` and `data/results`.
- `run()` = `run_pipeline(...)` → `analyze(...)` → writes `results.json` → prints a console summary (top influencers, communities, anomalies).
- Becomes the shared backbone for both the CLI and the FastAPI `/analyze` endpoint.

### 10.4 `app/verify.py` — the proof

Imports `run()`, then asserts the four checks from section 4:
1. **Cartel penetration** — how many of the 12 planted members land in the top-10 influencers (must be ≥50%).
2. **Kingpin** — exactly one, and it must be `Vikram Rathore`.
3. **Money-funnel** — a `money_funnel` anomaly exists, ideally pointing at the shell `Rathore Fabrics`.
4. **Communities** — cartel members must span ≥2 distinct communities.

Prints `PASS/FAIL`, returns exit code 0 (pass) / 1 (fail). This is our **automated judge-proof**.

### 10.5 `app/api.py` — the FastAPI backend

Endpoints:
- `GET /` — API info
- `GET /health` — liveness
- `GET /datasets` — which dataset has computed results
- `POST /analyze` — run the pipeline (synthetic by default, or switch to `real`) and return the JSON
- `GET /results` — last-computed results
- `GET /ui` — the dashboard HTML
- `GET /cytoscape.min.js` — Cytoscape.js, served locally so the demo works offline

> **Backend demo line:** "The dashboard doesn't hard-code the graph. Each *Re-analyze* click actually re-runs the Python analytics pipeline and we re-render whatever it returns — so what you see is live output, not a screenshot."

### 10.6 `run.py` — one-command control

A thin launcher that shells out to the right entry point based on the argument:
```
python run.py data       # regenerate synthetic dataset
python run.py pipeline   # extract + analyze -> results.json
python run.py verify     # end-to-end self-test
python run.py serve      # start dashboard at http://127.0.0.1:8000
python run.py all        # data -> pipeline -> verify (the full proof-on-demand)
```

---

## 11. How to set up and run (for every teammate)

### One-time setup (only needs doing once on a fresh machine)
```bash
# from D:\Project\SIH 2026
uv venv --python 3.11 .venv
VIRTUAL_ENV=.venv uv pip install -r requirements.txt
# optional but recommended — spaCy model (falls back to regex NER if absent):
VIRTUAL_ENV=.venv uv pip install spacy
.venv/Scripts/python -m spacy download en_core_web_sm
```
> **Windows pitfall (memorize):** if spaCy fails with `DLL load failed … msvcp140.dll`, install the **Microsoft Visual C++ Redistributable (x64)** and restart the shell. The system still runs without spaCy via the regex extractor.

### Every demo run
```bash
.venv/Scripts/python run.py all          # full proof: regen → analyze → verify PASSES
.venv/Scripts/python run.py serve        # dashboard at http://127.0.0.1:8000
```
Open **http://127.0.0.1:8000/ui**. Use the dataset selector to switch to **"Real police FIRs"** if you want to show real-data (run `scripts/real_firs.py` + `scripts/run_real.py` first).

---

## 12. How to explain it under pressure (cheat sheet)

- **"What is it?"** — "An AI system that reads fragmented crime data (FIRs, call records, bank transactions) and automatically builds the hidden relationship network, then tells you who the kingpin, launderer, and lieutenants are."
- **"How is it different?"** — "It doesn't just store data. It does cross-source *entity resolution* — linking the same person across files — then runs graph analytics that real investigators don't have time to do by hand, and it shows its work with plain-English anomaly alerts."
- **"Does it actually work?"** — Run `python run.py verify` and point at the PASS lines: it rediscovers the planted kingpin, launderer, and shell from noisy scattered files.
- **"Is it real data?"** — "It runs on both our synthetic demo *and* real Indian police FIRs from the ICDAR 2023 dataset."
- **"What's novel?"** — "The explainability: every edge has evidence (which source file), every anomaly has a readable reason, and we prove rediscovery end-to-end rather than just showing a pretty graph."

---

## 13. Repo layout cheat-sheet

```
SIH 2026/
├── run.py                  ← one-command launcher
├── requirements.txt        ← dependencies
├── README.md               ← project overview + setup
├── app/
│   ├── extract.py          ← NLP: NER + regex + entity resolution
│   ├── graph_analytics.py  ← NetworkX: centrality, communities, anomalies, roles
│   ├── pipeline.py         ← orchestrates extract → analyze → results.json
│   ├── verify.py           ← end-to-end proof (kingpin/launderer rediscovered)
│   ├── api.py              ← FastAPI backend
│   ├── ingest.py           ← real-world format adapters
│   └── dashboard.html      ← interactive network viz (Cytoscape.js)
├── scripts/
│   ├── gen_data.py         ← synthetic dataset generator (hides the cartel)
│   ├── real_firs.py        ← pull + parse ICDAR 2023 real FIRs
│   ├── run_real.py         ← run pipeline on real FIRs
│   └── _install.py         ← helper
├── data/
│   ├── synthetic/          ← firs/ cdrs/ banking/ (generated)
│   ├── real/               ← parsed real FIRs
│   └── results/            ← results.json, results_real.json
└── docs/DEMO_SCRIPT.md     ← live presentation script
```

---

*Last note for the team:* the two files to **understand cold** are `app/extract.py` (the NLP brain) and `app/graph_analytics.py` (the investigator's logic). Everything else is plumbing around them. If you can explain those two modules from memory, you can explain the whole project.