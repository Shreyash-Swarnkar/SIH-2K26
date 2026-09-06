"""
Entity & relationship extraction pipeline.

Inputs: raw unstructured text (FIRs / reports) + structured records (CDRs, transactions).
Output: a set of typed "entities" and a set of weighted "relations" that feed the
graph-builder. This is the NLP core of the system.

Design:
- Named-entity recognition (spaCy) for PERSONS, ORGS, GPES, DATES.
- Domain regex overlays for the high-signal crime artifacts spaCy is weak on:
  Indian phone numbers, vehicle registrations, FIR-case numbers, money amounts.
- Cross-source entity resolution:
    * A person surfaced in an FIR whose phone/vehicle recurs in a CDR/transaction
      is matched to the same canonical node via those stable identifiers.
- Custom relation extractor: when two entity types co-occur within the same document
  or firing window, an edge is created with a label + weight, plus the source evidence
  (which FIR/CDR/txn and what text).
"""
from __future__ import annotations
import os
import re
import json
from collections import defaultdict

import spacy

# ------------------------------------------------------------------ constants
PHONE_RE = re.compile(r"\b[987]\d{9}\b|\b\d{5}[-\s]?\d{5}\b")
VEHICLE_RE = re.compile(
    r"\b(?:[A-Z]{2}-\d{1,2}-[A-Z]{1,2}-\d{4}|[A-Z]{2}-\d{2}-[A-Z]{2}-\d{4})\b"
)
FIRNO_RE = re.compile(r"\b(?:FIR|EOW|case|Cr\.No\.)\s*[A-Z]*[-/:]?\s*(\d+)\s*/\s*(\d{4})\b", re.I)
AMOUNT_RE = re.compile(r"\b(?:Rs\.?|INR|₹|rupees)\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|lakhs|crore|crores|thousand|k)?\b", re.I)
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")

# Entities we track keyed by extractor; phone/vehicle are the canonical linkers.
ENTITY_TYPES = ("PERSON", "ORG", "LOC", "PHONE", "VEHICLE", "DATE", "AMOUNT", "FIR")

# Noise-words to drop from NER PERSON spans (common but not real names)
DROP_WORDS = {"the", "a", "an", "of", "resident", "complainant", "eyewitness",
              "suspect", "accused", "investigation", "including", "and"}


# =============================================================== spaCy loader
_nlp = None
def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"[extract] spaCy unavailable ({e}); using regex person extractor.")
            _nlp = False  # sentinel: means "no spaCy"
    return _nlp


# ------------------------------------------------------------------- regex NER fallback
# Pure-Python person extraction when spaCy can't load. Catches the Indian
# "First Last" / "First Middle Last" full-name pattern under "…, First Last,
#", "…by First Last", "in the name linked to First Last", "suspect First Last".
_PERSON_SENT_RE = re.compile(
    r"(?:(?:by|of|to|and|with|under|found|linked to|against|suspect(?:s)?|"
    r"complainant|eyewitness(?:es)?|witness(?:es)?|alleged|accused)\s+)"
    r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,2})"
)

# Generic capitalized non-person words spaCy may label PERSON
_NONPERSON_WORDS = {
    "registered", "central", "station", "road", "colony", "nagar", "market",
    "yard", "estate", "complex", "tower", "towers", "street", "lane", "no.",
    "no", "fir", "fir no.", "fir no", "case", "section", "dtd", "dated",
}

# Label / legal / station tokens that mark a span as NOT a human name, rejected
# anywhere in the span (independent of position). Handles real-FIR noise like
# "420/406 Ipc", "Baguiati Ps", "Ipc 279/338 Ipc", "Si ... Of Baguiati Ps",
# "Nscbi Airport".
_LABEL_TOKENS = {
    "ipc", "bns", "section", "sections", "sec", "secc", "ps", "p.s", "p.s.",
    "fir", "case", "cr", "no.", "no", "dtd", "dated", "of", "si", "psi", "api",
    "di", "dsp", "asi", "constable", "inspector", "sub-inspector", "subinspector",
    "complex", "station", "police", "year", "court", "office", "pswom", "psairport",
    "nscbi", "airport", "eow", "cyber", "crime", "women", "eco", "park",
    "baguiati", "rajarhat", "bidhannagar", "lake", "town", "electronics",
    "recruiting", "company", "director", "proprietor", "director of", "manager",
    "owner", "partner", "accused", "complainant", "informant", "witness",
    "victim", "relatives", "resident", "s/o", "d/o", "w/o", "c/o",
}

# Vehicle makes/model labels that spaCy systematically calls a PERSON
_VEHICLE_MAKES = {
    "mahindra bolero", "maruti swift", "innova", "eicher", "eicher pro",
    "mahindra", "maruti", "suzuki", "tata motors", "toyota", "hyundai",
    "tavera", "scorpio", "xylo", "bolero", "fortune", "tempo", "ashok leyland",
}

# Common non-person capitalized tokens to drop
_NONPERSON = {
    "Annual", "Central", "North", "South", "East", "West", "High", "Supreme",
    "Department", "Ministry", "Section", "Statement", "Investigation",
    "Registration", "Vehicle", "Contact", "Number", "Police", "Station", "Road",
    "Street", "Lane", "Morning", "Evening", "Night", "January", "February",
    "March", "April", "May", "June", "July", "August", "September", "October",
    "November", "December", "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday",
    # cities / places that follow "resident of", "near", "at"
    "Mumbai", "Navi", "Bombay", "Delhi", "Pune", "Thane", "Kochi", "Ludhiana",
    "Hyderabad", "Bangalore", "Bengaluru", "Chennai", "Kolkata", "Ahmedabad",
    "Jaipur", "Lucknow", "Nagpur", "India", "Andheri", "Vashi", "Bhiwandi",
    "Mulund", "Godrej", "JNPT", "Container", "Terminal", "Dumpyard", "Estate",
    "Industrial", "Market", "Wing", "Bureau", "Cell", "Branch",
}
_GEO_SUFFIX = ("mumbai", "delhi", "pune", "thane", "kochi", "ludhiana", "nagar",
               "pur", "bad", "city", "town", "estate", "terminal", "market",
               "dumpyard", "yard", "station", "police")


def extract_persons_regex(text: str) -> list:
    found = []
    for line in text.splitlines():
        for m in _PERSON_SENT_RE.finditer(line):
            name = clean_person(m.group(1))
            toks = name.split()
            if len(toks) >= 2 and all(t[0].isalpha() for t in toks) and \
               not ({t.strip(".'").lower() for t in toks} & _LABEL_TOKENS) and \
               toks[0] not in _NONPERSON and all(
                t not in _NONPERSON for t in toks[1:]
            ):
                # exclude geo suffixes: "Navi Mumbai", "Mulund Industrial Estate" etc.
                last = toks[-1].lower()
                if not any(last.endswith(suf) or name.lower().startswith(suf)
                           for suf in _GEO_SUFFIX):
                    found.append(name)
    return list(dict.fromkeys(found))


def _plausible_person(name: str) -> bool:
    """A person name must be >=2 words, all words alphabetic-led (rejects
    statute strings like "420/406 Ipc"), not a legal/station label, not a
    known non-person, and not a geographic/vehicle label. Guards against spaCy
    mislabels and the regex false-positives."""
    toks = name.split()
    if len(toks) < 2:
        return False
    # alphabetic-led tokens only -> kills "420/406 Ipc", "2 Of Acb", "2017"
    if not all(t[0].isalpha() for t in toks):
        return False
    # any legal/station/label token anywhere -> not a human name
    low = {t.strip(".'").lower() for t in toks}
    if low & _LABEL_TOKENS:
        return False
    if toks[0] in _NONPERSON or any(t in _NONPERSON for t in toks[1:]):
        return False
    last = toks[-1].lower()
    if any(last.endswith(suf) or name.lower().startswith(suf) for suf in _GEO_SUFFIX):
        return False
    if toks[-1].lower() in _NONPERSON_WORDS:  # generic capitalized noun
        return False
    if name.lower() in _VEHICLE_MAKES or toks[0].lower() in _VEHICLE_MAKES:
        return False
    return True


def extract_persons(text: str) -> list:
    """Person extraction: union of spaCy-PERSON (filtered) and the domain
    regex. The regex is authoritative for our synthetic schema; spaCy adds
    recall but is de-noised so car makes / city names never become people."""
    found = list(extract_persons_regex(text))
    nlp = get_nlp()
    if nlp:
        for ent in nlp(text).ents:
            if ent.label_ == "PERSON":
                name = clean_person(ent.text)
                if (
                    _plausible_person(name)
                    and name not in found
                    and name.lower() not in _VEHICLE_MAKES
                ):
                    found.append(name)
    return found


# =============================================================== regex tools
def extract_phones(text: str):
    return list(dict.fromkeys(PHONE_RE.findall(text)))


def extract_vehicles(text: str):
    return list(dict.fromkeys(VEHICLE_RE.findall(text)))


def extract_firnos(text: str):
    return list(dict.fromkeys(m[0] for m in FIRNO_RE.finditer(text)))


def extract_amounts(text: str):
    return list(dict.fromkeys(m[0] for m in AMOUNT_RE.finditer(text)))


def clean_person(span: str) -> str:
    """Normalise a spaCy PERSON span into a canonical full name if possible."""
    name = re.sub(r"\s+", " ", span).strip()
    # fold titles
    name = re.sub(r"^(mr|mrs|ms|dr|sri|shri|smt|complainant)\s+", "", name, flags=re.I)
    toks = [t for t in name.split() if t.lower() not in DROP_WORDS]
    return " ".join(toks) if toks else name


# =============================================================== text pipeline
def extract_from_text(text: str) -> dict:
    """Run NER + regex overlays on one unstructured document."""
    orgs, locs, dates = [], [], []
    got_ner = False
    nlp = get_nlp()
    if nlp:
        got_ner = True
        for ent in nlp(text).ents:
            lbl = ent.label_
            if lbl in ("ORG", "LAW"):
                orgs.append(ent.text)
            elif lbl in ("GPE", "LOC", "FAC"):
                locs.append(ent.text)
            elif lbl == "DATE":
                dates.append(ent.text)
    persons = extract_persons(text)
    if not got_ner:
        # purely regex fallback: also grab capitalized multi-word ORG-ish tokens
        pass
    return {
        "PERSON": list(dict.fromkeys(p for p in persons if p)),
        "ORG": list(dict.fromkeys(orgs)),
        "LOC": list(dict.fromkeys(locs)),
        "DATE": list(dict.fromkeys(dates)),
        "PHONE": extract_phones(text),
        "VEHICLE": extract_vehicles(text),
        "AMOUNT": extract_amounts(text),
        "FIR": extract_firnos(text),
    }


# =============================================================== CDR / txn parsers
def parse_cdr_path(path: str) -> list[dict]:
    """Parse a CDR pipe-text file -> list of {from, to, ts, dur, cell, type}."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith(("cdr", "header")):
                continue
            parts = line.split("|")
            if len(parts) < 5:
                continue
            rows.append(dict(
                from_=parts[0].strip(), to=parts[1].strip(), ts=parts[2].strip(),
                dur=int(parts[3] or 0), cell=parts[4].strip(),
                type=parts[5].strip() if len(parts) > 5 else "voice",
            ))
    return rows


def parse_txn_path(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith(("date", "txn")):
                continue
            parts = line.split("|")
            if len(parts) < 5:
                continue
            rows.append(dict(
                date=parts[0].strip(), txn_id=parts[1].strip() if len(parts) > 1 else "",
                from_=parts[2].strip(), to=parts[3].strip(),
                amt=parts[4].strip(), mode=parts[5].strip() if len(parts) > 5 else "",
                remarks=parts[6].strip() if len(parts) > 6 else "",
            ))
    return rows


# =============================================================== entity store
class EntityStore:
    """Canonical entities resolved across all sources; dedups by stable id."""
    def __init__(self):
        self.by_id = {}
        self.by_phone = {}
        self.by_vehicle = {}
        self.by_name = {}
        self._seq = 0

    def register(self, typ, value, source=None, **attrs):
        key = self._canon(key_value := (typ, self._norm(value)))
        if key in self.by_id:
            e = self.by_id[key]
            if source and source not in e["sources"]:
                e["sources"].append(source)
            return e["id"]
        e = {**attrs,
             "id": f"{typ}_{self._seq}", "type": typ, "value": value,
             "key": key_value, "sources": [source] if source else []}
        self._seq += 1
        self.by_id[key] = e
        if typ == "PHONE": self.by_phone[self._norm(value)] = e["id"]
        if typ == "VEHICLE": self.by_vehicle[self._norm(value)] = e["id"]
        self.by_name[key] = e["id"]
        return e["id"]

    @staticmethod
    def _norm(v): return re.sub(r"[\s\-_]+", "", str(v)).lower()

    def _canon(self, kv):
        typ, norm = kv
        # persons resolve by exact name; phones/vehicles by their normalized key
        if typ == "PHONE" and norm in self.by_phone:
            return ("PHONE", norm)
        if typ == "VEHICLE" and norm in self.by_vehicle:
            return ("VEHICLE", norm)
        return kv

    def all(self):
        return list(self.by_id.values())

    def attach(self, entity_id, **attrs):
        e = self.by_id.get(entity_id)
        if e: e.update({k: v for k, v in attrs.items() if v})


# =============================================================== relation store
class RelationStore:
    def __init__(self):
        self.edges = {}  # (u,v) -> {weight, kinds:[], evidence:[], directed:[(s,t)]}

    def add(self, u, v, kind, weight=1.0, evidence=None):
        if u == v:
            return
        key = (min(u, v), max(u, v))
        e = self.edges.setdefault(key, {"weight": 0.0, "kinds": [],
                                        "evidence": [], "directed": []})
        e["weight"] += weight
        if kind not in e["kinds"]:
            e["kinds"].append(kind)
        if evidence and (not e["evidence"] or e["evidence"][-1] != evidence):
            e["evidence"].append(evidence)
        # preserve direction for money-flow (u sends to v)
        if kind == "money":
            e["directed"].append((u, v))

    def all(self):
        return [dict(u=u, v=v, **d) for (u, v), d in self.edges.items()]


# =============================================================== orchestrator
def run_pipeline(fir_dir, cdr_dir, bank_dir) -> dict:
    """Run the full extraction over the synthetic dataset. Returns entities+edges."""
    store = EntityStore()
    rels = RelationStore()

    # person<->phone / person<->vehicle ownership map (identity resolution)
    person_id_by_phone = {}
    person_id_by_vehicle = {}

    # ---- unstructured: FIRs
    for fn in sorted(os.listdir(fir_dir)):
        if not fn.lower().endswith((".txt", ".md")):
            continue
        path = os.path.join(fir_dir, fn)
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        ents = extract_from_text(text)
        node_ids = {}
        for et, values in ents.items():
            for v in values:
                node_ids.setdefault(et, []).append(store.register(et, v, source=fn))

        # co-occurrence edges between linker types within the doc
        LINKER = {"PERSON", "PHONE", "VEHICLE", "ORG"}
        linker_ids = [i for et in LINKER for i in node_ids.get(et, [])]
        for i, a in enumerate(linker_ids):
            for b in linker_ids[i+1:]:
                rels.add(a, b, "co-occur", weight=1.0, evidence=f"{fn}")

        # identity resolution: a phone/vehicle belongs to the person whose name
        # appears nearest in the same document (proximity match).
        id2ent = {e["id"]: e for e in store.all()}
        persons = node_ids.get("PERSON", [])
        for ph in node_ids.get("PHONE", []):
            ph_val = id2ent[ph]["value"]
            # position of phone in text (first occurrence)
            ph_pos = text.find(ph_val)
            best, best_d = None, 1e9
            for pid in persons:
                p_val = id2ent[pid]["value"]
                p_pos = text.find(p_val)
                if p_pos >= 0 and abs(ph_pos - p_pos) < best_d:
                    best_d, best = abs(ph_pos - p_pos), pid
            if best is not None:
                person_id_by_phone[ph] = best
                store.attach(best, phone=ph_val)
        for vh in node_ids.get("VEHICLE", []):
            vh_val = id2ent[vh]["value"]
            vh_pos = text.find(vh_val)
            best, best_d = None, 1e9
            for pid in persons:
                p_val = id2ent[pid]["value"]
                p_pos = text.find(p_val)
                if p_pos >= 0 and abs(vh_pos - p_pos) < best_d:
                    best_d, best = abs(vh_pos - p_pos), pid
            if best is not None:
                person_id_by_vehicle[vh] = best
                store.attach(best, vehicle=vh_val)

    # ---- structured: CDRs (phone<->phone call graph, resolved to persons)
    for fn in sorted(os.listdir(cdr_dir)) if os.path.isdir(cdr_dir) else []:
        path = os.path.join(cdr_dir, fn)
        for r in parse_cdr_path(path):
            a = store.register("PHONE", r["from_"], source=fn)
            b = store.register("PHONE", r["to"], source=fn)
            rels.add(a, b, "call", weight=1.0, evidence=f"{fn} call")

    # ---- structured: transactions (account<->account money flow)
    for fn in sorted(os.listdir(bank_dir)) if os.path.isdir(bank_dir) else []:
        if not fn.lower().endswith((".csv", ".txt")):
            continue
        path = os.path.join(bank_dir, fn)
        for t in parse_txn_path(path):
            a = store.register("ACCOUNT", t["from_"], source=fn)
            b = store.register("ACCOUNT", t["to"], source=fn)
            w = 1.0 + min(float(t["amt"].replace(",", "")) / 1e6, 10.0)
            rels.add(a, b, "money", weight=w,
                     evidence=f"{fn} txn {t['txn_id']}")

    # ---- final: merge a phone/vehicle/account node into its owning person node.
    # Re-point every relation edge whose endpoint is a resolved node
    # onto the person, and drop the now-redundant node.
    merged = {}  # old id -> new(person) id
    for ph, pid in person_id_by_phone.items():
        merged[ph] = pid
    for vh, pid in person_id_by_vehicle.items():
        merged[vh] = pid
    # account name contains a known person's full name -> that person
    person_by_name = {}
    for ent in store.all():
        if ent["type"] == "PERSON":
            person_by_name[ent["value"].strip().lower()] = ent["id"]
    for ent in store.all():
        if ent["type"] != "ACCOUNT":
            continue
        base = ent["value"].replace("a/c", "").replace("account", "").strip(" .-")
        if base.strip().lower() in person_by_name:
            merged[ent["id"]] = person_by_name[base.strip().lower()]

    final_edges = []
    for e in rels.all():
        u, v = e["u"], e["v"]
        u = merged.get(u, u)
        v = merged.get(v, v)
        if u == v:
            continue
        final_edges.append({**e, "u": u, "v": v})

    entities = [ent for ent in store.all() if ent["id"] not in merged]

    # ---- attach net money flow (+receiver / -sender) to each person/account
    # using the preserved directed money edges (post-merge).
    net_money = {}
    for e in final_edges:
        for s, t in e.get("directed", []):
            s2, t2 = merged.get(s, s), merged.get(t, t)
            w = e["weight"]
            net_money[s2] = net_money.get(s2, 0) - w
            net_money[t2] = net_money.get(t2, 0) + w
    for ent in entities:
        net = net_money.get(ent["id"], 0)
        if net != 0:
            ent["net_money"] = round(net, 2)

    return {"entities": entities, "edges": final_edges}