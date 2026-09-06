# 🎯 Demo script & pitch — SIH 2026

A 5-minute live demo that lands the killer story: **the AI uncovers a hidden
criminal network from fragmented, noisy records.**

---

## The 60-second elevator pitch

> "Police records are fragmented — an FIR here, a phone log there, a suspicious
> bank transfer in between — and the connections are invisible. Our system reads
> those raw records, extracts every person, phone, vehicle and account with NLP,
> and rebuilds the hidden relationship network. Then graph analytics answer the
> two questions investigators actually ask: *who's in the gang*, and *who runs
> it* — surfacing roles like the kingpin, the money launderer, and the shell
> company — on a live network map."

---

## Live demo flow (3–4 min)

1. **Start** — `python run.py all` (regenerates data, runs pipeline, verifies)
   then `python run.py serve`, open `http://127.0.0.1:8000`.
2. **The problem** — show raw inputs: an unstructured FIR `.txt`, the CDR dump,
   the bank CSV. Point out: *no one line reveals the criminal network*.
3. **The system in action** — click **Re-analyze**. Watch it (a) extract
   entities across all sources, (b) build the graph, (c) color communities,
   (d) rank influencers **with role badges**.
4. **The reveal** — highlight:
   - **Vikram Rathore — `kingpin`**: few direct ties, but a bridge *and* the
     money sink. The quiet controller the raw data hides.
   - **Rajesh Kulkarni — `financier`**: the launderer, #1 threat, huge outflows.
   - **Rathore Fabrics Pvt Ltd — shell** flagged `money_funnel`.
   - A lieutenant like **Imran Shaikh** bridging his sub-group.
5. **Click a node** — show the evidence trail (which FIRs/CDRs tie the person to
   their phone, account, co-accused) and the threat meter.
6. **Prove it** — `python run.py verify` prints `PASS: 4 FAIL: 0`: the system
   independently rediscovered the gang + kingpin that was embedded in the raw
   data.

---

## Slides / PPT talking points

### 1. Problem
- Law-enforcement intelligence is siloed (FIRs, CDRs, banking, surveillance,
  social media) → hidden structure is invisible to manual review.
- Data is **unstructured** (narratives) and **noisy**; volume outpaces analysts.

### 2. Our solution — one sentence
- NLP entity extraction + knowledge-graph construction + graph analytics =
  **automatic discovery of criminal networks and who controls them.**

### 3. Pipeline (the technical muscle)
- **Extraction** — spaCy NER + domain regex (Indian phones, vehicle plates, FIR
  numbers) + **cross-source entity resolution** (a name in an FIR is the same
  entity as a CDR phone number and a bank account — we merge them).
- **Graph** — NetworkX: betweenness/eigenvector/degree centrality, Louvain
  community detection (gangs), weighted multi-role edges (call / money / same-FIR).
- **Detection** — rule + structural anomalies: money funnel, high-traffic node.
- **Role classifier** — bridges money-sink/funnel signals into *kingpin /
  financier / lieutenant / associate*.
- **Front-end** — FastAPI + interactive Cytoscape network dashboard.

### 4. Demo (the money slide)
- Show the graph, the role badges, the evidence trail on click.

### 5. Why it works (the "aha")
- Real criminal SNA insight: **the kingpin is rarely the busiest node.** We use
  articulation-point (bridge) detection + money-flow direction, not raw degree,
  so the quiet controller surfaces — not just the loudest talker.

### 6. Impact & roadmap
- Cut investigation triage time; surface leads analysts would miss.
- Roadmap: social-media/sentiment ingestion, temporal link analysis, Neo4j at
  scale, natural-language query over the graph, alerting.

### 7. Feasibility & data safety
- Built on **open data** (public police/crime datasets) + synthetic data —
  no privacy risk; production-ready for classified inputs behind vetted infra.

---

## Anticipate the judges' questions

| Question | Answer |
|---|---|
| Is this just u-something vs graph? | It's the **integration** — extraction + entity resolution + structural role inference. The role detection (kingpin vs launderer) is domain-specific and novel. |
| How accurate? | Synthetic full pipeline verified; real-data adapter (`app/ingest.py`) accepts standard CSV bundles. On real records, precision depends on source quality — we report evidence per edge for manual verification. |
| Why these metrics? | Betweenness = gatekeeper; eigenvector = connected-to-important people; money direction disambiguates kingpin (receiver) from launderer (funnel). We normalize so money can't drown structure. |
| Scale? | NetworkX handles the demo; swap to Neo4j/GraphX for production scale. |
| Chinese-input support / real FIRs? | Extraction is language-agnostic at the regex layer; spaCy + the Indian-data model handle Hindi-English code-mixed text. |