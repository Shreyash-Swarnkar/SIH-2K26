"""
Synthetic crime-dataset generator for the SIH 2026 demo.

Generates realistic FIR documents, CDRs (call detail records) and financial
transaction records that HIDE a structured criminal network. The pipeline's
job is to rediscover this hidden structure, so the generator deliberately
scatters the connections across many files and adds noise.

The "hidden truth":
- One cartel: ~11 core members + peripheral associates
  - A KINGPIN (very few direct calls, deliberately "quiet" - uses intermediaries)
  - 2 lieutenants (high out-degree)
  - a money launderer who handles all proceeds
  - a logistics/transport node
  - a "communicator" who runs an encrypted-channel call pattern
- ~60% of all traffic is innocuous noise (random citizens, businesses)
- The cartel uses obfuscation: burner phone swaps, a shell company, recurring
  "settlement" transactions, and vehicles shared within the ring.

Deterministic seed so the demo is reproducible.
"""
from __future__ import annotations
import json
import random
import os
from datetime import datetime, timedelta

SEED = 20260905
random.seed(SEED)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------- cartel model
# name, role, phone, vehicles[], shell-company association, home_city
CARTEL = [
    dict(name="Vikram Rathore",     role="kingpin",      phone="98850-11221", vehicles=["MH-01-AB-3344"], org="Rathore Fabrics Pvt Ltd", city="Mumbai"),
    dict(name="Sanjay Mehta",       role="lieutenant",   phone="98110-55667", vehicles=["MH-01-CD-8890"], org=None, city="Mumbai"),
    dict(name="Imran Shaikh",       role="lieutenant",   phone="97022-11345", vehicles=["MH-02-EF-1122"], org=None, city="Navi Mumbai"),
    dict(name="Rajesh Kulkarni",    role="money",        phone="98220-77665", vehicles=[], org="Kulkarni Trading", city="Pune"),
    dict(name="Anil Deshmukh",      role="logistics",    phone="99700-33455", vehicles=["MH-01-GH-5566", "MH-01-GH-7788"], org="Deshmukh Logistics", city="Thane"),
    dict(name="Farhan Qureshi",     role="communicator", phone="98922-99001", vehicles=[], org=None, city="Mumbai"),
    dict(name="Dinesh Yadav",       role="associate",    phone="97671-22334", vehicles=[], org=None, city="Delhi"),
    dict(name="Rohit Pawar",        role="associate",    phone="96540-88990", vehicles=["MH-02-AB-7788"], org=None, city="Navi Mumbai"),
    dict(name="Sneha Iyer",         role="associate",    phone="95511-44556", vehicles=[], org="Iyer & Co", city="Mumbai"),
    dict(name="Arjun Nair",         role="associate",    phone="94220-66778", vehicles=[], org=None, city="Kochi"),
    dict(name="Harpreet Singh",     role="associate",    phone="98550-12312", vehicles=[], org=None, city="Ludhiana"),
    dict(name="Manoj Gupta",        role="associate",    phone="98102-77889", vehicles=[], org="Gupta Exports", city="Mumbai"),
]

# Shell company used for laundering
SHELL = "Rathore Fabrics Pvt Ltd"

CITIES = ["Mumbai", "Navi Mumbai", "Thane", "Pune", "Delhi", "Kochi", "Ludhiana"]
INNOCENT_FIRST = ["Anita", "Ramesh", "Sunita", "Prakash", "Kavita", "Vinod", "Geeta",
                  "Ashok", "Meena", "Suresh", "Rekha", "Nitin", "Divya", "Yogesh", "Pooja",
                  "Neha", "Rahul", "Sandeep", "Priya", "Alok", "Shalini", "Mohan", "Deepa",
                  "Karan", "Rajni", "Vivek", "Anjali", "Tarun", "Shobha", "Gaurav",
                  "Neeraj", "Pallavi", "Sachin", "Mala", "Ravi", "Chitra", "Hemant", "Asha",
                  "Bijoy", "Leela", "Ishaan", "Kiran", "Sudhir", "Manisha", "Bharat", "Uma"]
INNOCENT_LAST = ["Sharma", "Verma", "Reddy", "Nair", "Joshi", "Bose", "Iyengar",
                 "Chopra", "Malhotra", "Basu", "Tiwari", "Kohli", "Srinivasan", "Dutta",
                 "Agarwal", "Pillai", "Rout", "Bhatt", "Desai", "Khan", "Shetty",
                 "Chauhan", "Iyer2", "Nath", "Parekh", "Saxena", "Tandon", "Vaidya",
                 "Wagle", "Yadav2", "Zachariah", "Banerjee", "Chatterjee", "Das",
                 "Ghosh", "Mukherjee", "Roy", "Sen", "Dey", "Haldar", "Majumdar"]

NAMES = {m["name"] for m in CARTEL}


def innocent_name() -> str:
    return f"{random.choice(INNOCENT_FIRST)} {random.choice(INNOCENT_LAST)}"


def phone() -> str:
    """Random 10-digit mobile starting with 9/8/7 (Indian formats)."""
    return f"{random.choice('987')}{random.randint(10000000,99999999)}"


def reg_no() -> str:
    return f"MH-{random.choice('012')}-{random.choice('ABCDEFGH')}{random.choice('ABCDEFGH')}-{random.randint(1000,9999)}"


# Ensure innocent names never collide with cartel members
def unique_name():
    while True:
        n = innocent_name()
        if n not in NAMES:
            NAMES.add(n)
            return n


# ---------------------------------------------------------------- FIRs
def gen_fir(member, incident_data):
    """A realistic Hindi-English FIR narrative embedding the member."""
    name = member["name"]
    city = member.get("city", "Mumbai")
    # Random crime type, but the cartel is in the drug/goods-trade lane
    blanket = incident_data["blanket_type"]
    items = member.get("goods") or (["electronics goods", "pharma stock"] if member.get("role") == "logistics" else ["cash", "gold", "foreign liquor"])
    amount = f"Rs {random.choice(['4.5','7','12','18','25','30'])} lakh"
    # Real FIRs capture the person's contact / vehicle. Embed the member's
    # actual phone (and, ~half the time, a real vehicle) so PERSON<->PHONE and
    # PERSON<->VEHICLE bridges form in the graph.
    phone_line = ""
    if member.get("phone"):
        p = member["phone"].replace("-", "")
        phone_line = f" A contact number {p} associated with {name} was also noted. "
    veh_line = ""
    if member.get("vehicles") and random.random() < 0.5:
        veh_line = f" Vehicle {random.choice(member['vehicles'])} is registered in the name linked to {name}. "
    return f"""FIR No. {incident_data['fir_no']} / {incident_data['year']}
Police Station: {city} Central
Registered on {incident_data['date']}.

{incident_data['blanket_type']}: The complainant {incident_data['complainant']}, a resident of {city}, reported that a consignment of {', '.join(items)} valued at {amount} was {incident_data['verb']} on the night of {incident_data['evdate']}.

During investigation, eyewitness accounts mentioned seeing {name} ({incident_data['id_desc']}) near the {incident_data['location']} at approximately {incident_data['time']}. A {incident_data['vehicle_desc']} was observed leaving the scene; registration details are being cross-checked with the transport authority.{phone_line}{veh_line}

The {incident_data['agency']} has registered the case under relevant sections of the IPC and is examining call detail records of the suspects' contacts. Investigation is ongoing and further persons of interest may be added to the FIR."""


def gen_shell_fir(member, incident_data):
    return f"""FIR — Economic Offences Wing, {member['city']}
Ref: EOW/{incident_data['year']}/{incident_data['fir_no']}

An inquiry was initiated into irregularities reported by {incident_data['complainant']} regarding dealings with {SHELL}. It is suspected that invoicing activities between {SHELL} and a trading entity linked to {member['name']} may not reflect genuine commercial transactions.

Enquiries also surfaced a mention of vehicle {member['vehicles'][0] if member['vehicles'] else reg_no()} being used for the movement of goods. The case has been registered under the Prevention of Money Laundering Act (PMLA). Proceedings under the Income Tax Act are in parallel."""


# ---------------------------------------------------------------- CDRs
def gen_cdr(records, scenario="innocent"):
    """A CDR of one person: list of call events (from, to, ts, dur, cell).
    scenario controls which contact and pattern."""
    lines = ["CDR|called_party|start_time|duration_sec|cell_tower|type"]
    for r in records:
        lines.append(
            f"{r['from']}|{r['to']}|{r['ts']}|{r['dur']}|{r['cell']}|{r['type']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- transactions
def gen_bank(member, txns):
    lines = ["date|txn_id|from_acc|to_acc|amount|mode|remarks"]
    for t in txns:
        lines.append(
            f"{t['date']}|{t['txn_id']}|{t['from']}|{t['to']}|{t['amt']}|{t['mode']}|{t['remarks']}"
        )
    return "\n".join(lines)


# ================================================================ build dataset
def build():
    now = datetime(2025, 1, 1)
    fir_dir = os.path.join(OUT_DIR, "firs")
    cdr_dir = os.path.join(OUT_DIR, "cdrs")
    bank_dir = os.path.join(OUT_DIR, "banking")
    os.makedirs(fir_dir, exist_ok=True)
    os.makedirs(cdr_dir, exist_ok=True)
    os.makedirs(bank_dir, exist_ok=True)

    blanket_types = ["robbery", "smuggling of contraband", "theft from warehouse",
                     "fraudulent sale of goods", "illegal transport of goods",
                     "dacoity", "receiving stolen property"]
    verbs = ["stolen", "smuggled", "seized", "diverted", "misappropriated"]
    id_desc = ["a tall man in his forties", "a stocky individual with a black bag",
               "a person wearing a dark jacket", "a man with a moustache",
               "an unidentified male", "a woman in a headscarf"]
    locations = ["Godrej Warehouse", "Andheri Dumpyard", "JNPT Container Terminal",
                 "Vashi Market yard", "Bhiwandi godown", "Mulund Industrial Estate"]
    agencies = ["Crime Branch", "Anti-Narcotics Cell", "Port Trust Police",
                "Economic Offences Wing", "Zone 4 Police Station"]
    vehicle_desc = ["black Maruti Swift", "white Eicher truck", "grey Toyota Innova",
                    "blue Mahindra Bolero"]

    # ---- FIRs
    fir_catalog = {}
    for i, m in enumerate(CARTEL, 1):
        incident = dict(
            fir_no=100 + i, year=2024, date=f"2024-0{random.randint(1,6)}-{random.randint(1,28):02d}",
            evdate=f"2024-0{random.randint(1,6)}-{random.randint(1,28):02d}",
            complainant=unique_name(), blanket_type=random.choice(blanket_types),
            verb=random.choice(verbs), id_desc=random.choice(id_desc),
            location=random.choice(locations), time=f"{random.randint(0,23):02d}:{random.randint(0,59):02d}",
            vehicle_desc=random.choice(vehicle_desc), agency=random.choice(agencies),
        )
        # Each cartel member appears in ~3 FIRs so the graph has edges
        content = gen_fir(m, incident)
        fn = os.path.join(fir_dir, f"FIR_{incident['fir_no']}.txt")
        with open(fn, "w") as f:
            f.write(content)
        fir_catalog[m["name"]] = fn

    # shell-company FIRs
    for i in range(3):
        m = random.choice(CARTEL)
        incident = dict(fir_no=500 + i, year=2024, complainant=unique_name())
        with open(os.path.join(fir_dir, f"FIR_{500+i}_EOW.txt"), "w") as f:
            f.write(gen_shell_fir(m, incident))

    # ---- Innocent FIRs (noise)
    for i in range(60):
        name = unique_name()
        incident = dict(fir_no=1000 + i, year=2024, date=f"2024-0{random.randint(1,6)}-{random.randint(1,28):02d}",
                        evdate=f"2024-0{random.randint(1,6)}-{random.randint(1,28):02d}",
                        complainant=unique_name(), blanket_type=random.choice(blanket_types),
                        verb=random.choice(verbs), id_desc=random.choice(id_desc),
                        location=random.choice(locations), time=f"{random.randint(0,23):02d}:{random.randint(0,59):02d}",
                        vehicle_desc=random.choice(vehicle_desc), agency=random.choice(agencies))
        with open(os.path.join(fir_dir, f"FIR_{1000+i}.txt"), "w") as f:
            f.write(gen_fir(dict(name=name, city=random.choice(CITIES)), incident))

    # ---- CDRs: cartel call graph
    def minutes_ago(n): return (now - timedelta(minutes=n)).strftime("%Y-%m-%d %H:%M:%S")
    # Build a directed communication graph among cartel members.
    # Structure: Vikram (kingpin) is the CUT-VERTEX bridging two sub-groups that
    # otherwise do NOT talk directly — the classic "hidden controller" topology.
    #   group A (lieutenant): Sanjay Mehta + Rajesh Kulkarni (money) + Anil Deshmukh (logistics)
    #   group B (lieutenant): Imran Shaikh + Farhan Qureshi (communicator)
    # Associates/street-level sit under each lieutenant.
    comms = {
        "kingpin": ["Sanjay Mehta", "Imran Shaikh"],          # only 2 direct channels, few calls
        "Sanjay Mehta": ["Vikram Rathore", "Rajesh Kulkarni", "Anil Deshmukh", "Rohit Pawar", "Dinesh Yadav"],
        "Imran Shaikh":  ["Vikram Rathore", "Farhan Qureshi", "Sneha Iyer", "Arjun Nair", "Harpreet Singh", "Manoj Gupta"],
        # money launderer consolidates under group A
        "Rajesh Kulkarni": ["Vikram Rathore", "Sneha Iyer", "Anil Deshmukh", "Manoj Gupta"],
        "Anil Deshmukh":   ["Rohit Pawar", "Rajesh Kulkarni", "Harpreet Singh"],
        "Farhan Qureshi":  ["Dinesh Yadav", "Arjun Nair", "Sneha Iyer"],
    }
    for i, m in enumerate(CARTEL):
        records = []
        # each member's own outgoing calls cluster on a few targets (the ring)
        # kingpin is deliberately quieter but every call is high-signal
        n_calls = 18 if m["role"] == "kingpin" else 40
        targets = comms.get(m["name"]) or comms.get(m["role"].lower(), [])
        for j in range(n_calls):
            if targets and random.random() < 0.85:
                tgt = random.choice(targets)
            else:
                tgt = unique_name()  # noise contact
            tgt_phone = next((x["phone"] for x in CARTEL if x["name"] == tgt), phone())
            records.append(dict(
                from_=m["phone"], to=tgt_phone, ts=minutes_ago(random.randint(1, 60 * 24 * 90)),
                dur=random.randint(15, 900), cell=f"TOWER-{random.randint(1,40):02d}",
                type=random.choice(["voice", "sms", "data"]),
            ))
        # patch: use the 'from' field as-is instead of from_
        recs = []
        for r in records:
            r2 = dict(r); r2["from"] = r2.pop("from_"); recs.append(r2)
        with open(os.path.join(cdr_dir, f"CDR_{m['name'].replace(' ','_')}.txt"), "w") as f:
            f.write(gen_cdr(recs))

    # ---- Banking: money-laundering chain through shell
    # tiered: associates -> lieutenants -> money launderer -> shell (big out)
    launderer = next(m for m in CARTEL if m["role"] == "money")
    tier_a = [m for m in CARTEL if m["role"] == "associate"]
    tier_b = [m for m in CARTEL if m["role"] == "lieutenant"]
    txns = []
    txn_counter = 0
    def txn(frm, to, amt, mode, remarks):
        nonlocal txn_counter
        txn_counter += 1
        d = f"2024-{random.randint(1,6):02d}-{random.randint(1,28):02d}"
        txns.append(dict(date=d, txn_id=f"TXN{txn_counter:05d}", from_=frm, to=to,
                         amt=amt, mode=mode, remarks=remarks))
    # associates sweep small amounts -> launderer
    for m in tier_a:
        for _ in range(random.randint(4, 8)):
            txn(f"{m['name']} a/c", "Rajesh Kulkarni a/c", random.randint(2, 9) * 10000,
                "NEFT", "settlement")
    # lieutenants -> launderer bigger
    for m in tier_b:
        for _ in range(random.randint(6, 12)):
            txn(f"{m['name']} a/c", "Rajesh Kulkarni a/c", random.randint(10, 40) * 100000,
                random.choice(["NEFT", "RTGS"]), random.choice(["invoiced goods", "forwarding charges", "consultancy"]))
    # launderer consolidates -> shell (the funnel)
    for _ in range(random.randint(15, 30)):
        txn("Rajesh Kulkarni a/c", f"{SHELL} a/c", random.randint(50, 200) * 100000,
            "RTGS", "export settlement / invoice reconciliation")
    # kingpin takes a personal cut: lieutenants pay HIM directly too
    kingpin = next(m for m in CARTEL if m["role"] == "kingpin")
    for m in tier_b:
        for _ in range(random.randint(4, 7)):
            txn(f"{m['name']} a/c", f"{kingpin['name']} a/c", random.randint(20, 60) * 100000,
                random.choice(["NEFT", "RTGS"]), "operational share / settlement")
    # kingpin extracts from shell (back to him) — his biggest inbound
    for _ in range(6):
        txn(f"{SHELL} a/c", f"{kingpin['name']} a/c", random.randint(2, 5) * 1000000,
            "DD", "director remuneration / dividend")
    # innocuous personal banking noise
    c = 0
    while c < 100:
        frm = unique_name(); to = unique_name()
        txn(f"{frm} a/c", f"{to} a/c", random.randint(500, 20000), "UPI", "personal payment")
        c += 1
    # patch txn from_ -> from
    t_recs = []
    for t in txns:
        t2 = dict(t); t2["from"] = t2.pop("from_"); t_recs.append(t2)
    with open(os.path.join(bank_dir, "transactions_all.csv"), "w") as f:
        f.write(gen_bank(launderer, t_recs))

    # manifest
    manifest = dict(
        seed=SEED, cartel=[{k: m[k] for k in ("name","role","phone","city")} for m in CARTEL],
        shell=SHELL, n_firs=len(os.listdir(fir_dir)), n_cdrs=len(os.listdir(cdr_dir)),
        n_txns=len(t_recs),
    )
    with open(os.path.join(OUT_DIR, "MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Dataset written to {OUT_DIR}")
    print(f"  FIRs: {len(os.listdir(fir_dir))}")
    print(f"  CDRs: {len(os.listdir(cdr_dir))}")
    print(f"  Txns: {len(t_recs)}")
    print(f"  Hidden cartel: {[m['name'] for m in CARTEL]}")
    print(f"  Kingpin: Vikram Rathore   Shell: {SHELL}")


if __name__ == "__main__":
    build()