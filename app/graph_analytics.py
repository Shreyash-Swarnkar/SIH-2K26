"""
Graph analytics on the extracted entity-relation network.

Turns entities + weighted edges into:
  - A NetworkX graph with communities (gangs).
  - Centrality scores -> key influencers / kingpin detection.
  - Anomaly detection scoring (money-funnel, eccentric-communicator, isolation).

Scoring philosophy (explained as we go):
  * Betweenness centrality → who bridges sub-networks = "the fixer"/kingpin.
  * Degree/strength → who communicates or moves the most money = activity hub.
  * Louvain community detection → modular gangs that our graph naturally clusters.
  * Composite "threat score" = normalized blend of the above + anomaly flags,
    so the dashboard can rank suspects and highlight the cartel core.
"""
from __future__ import annotations
from collections import defaultdict

import networkx as nx

try:
    import community as python_louvain
    HAVE_LOUVAIN = True
except Exception:
    HAVE_LOUVAIN = False


def build_graph(entities, edges) -> nx.Graph:
    """Build undirected weighted graph; nodes carry entity attrs."""
    G = nx.Graph()
    id2ent = {e["id"]: e for e in entities}
    for e in entities:
        G.add_node(e["id"], **e)
    for ed in edges:
        u, v = ed["u"], ed["v"]
        w = ed.get("weight", 1.0)
        if G.has_edge(u, v):
            G[u][v]["weight"] += w
            for k in ed.get("kinds", []):
                if k not in G[u][v].setdefault("kinds", []):
                    G[u][v]["kinds"].append(k)
        else:
            G.add_edge(u, v, weight=w, kinds=list(ed.get("kinds", [])),
                       evidence=list(ed.get("evidence", []))[:3])
    return G


def add_centrality(G: nx.Graph) -> None:
    """Attach centrality metrics on every node."""
    ids = list(G.nodes())
    n = max(len(ids), 2)
    bc = nx.betweenness_centrality(G, weight="weight", k=min(n, 200))
    dc = nx.degree_centrality(G)
    # weighted strength (sum of incident weights)
    strength = {nd: float(sum(d["weight"] for _, d in G[nd].items())) for nd in ids}
    # eigenvector centrality: connected to important people = "quiet controller"
    try:
        ec = nx.eigenvector_centrality(G, weight="weight", max_iter=1000)
    except Exception:
        ec = {nd: dc.get(nd, 0) for nd in ids}
    for nd in ids:
        G.nodes[nd]["betweenness"] = round(bc.get(nd, 0), 5)
        G.nodes[nd]["degree"] = round(dc.get(nd, 0), 5)
        G.nodes[nd]["strength"] = round(strength.get(nd, 0), 4)
        G.nodes[nd]["eigenvector"] = round(ec.get(nd, 0), 5)


def community_label(G: nx.Graph) -> None:
    if not HAVE_LOUVAIN:
        # fallback: connected components
        for i, comp in enumerate(nx.connected_components(G)):
            for nd in comp:
                G.nodes[nd]["community"] = i
        return
    partition = python_louvain.best_partition(G, weight="weight", random_state=42)
    for nd, com in partition.items():
        G.nodes[nd]["community"] = com


def detect_anomalies(G: nx.Graph) -> list[dict]:
    """Rules-based anomaly flags. Returns list of {entity_id, flag, note}."""
    flags = []
    # 1) Money-funnel: an account whose out-edges concentrate on ONE huge target
    for nd in G.nodes():
        if G.nodes[nd]["type"] != "ACCOUNT":
            continue
        out_tot = sum(d["weight"] for _, d in G[nd].items())
        if out_tot <= 0:
            continue
        top = max(G[nd].values(), key=lambda d: d["weight"])
        if top["weight"] > 0.55 * out_tot and out_tot > 5:
            flags.append(dict(entity_id=nd, flag="money_funnel",
                              note="Account funnels most value to a single recipient"))
    # 2) Network hub with odd phone traffic (many unique contacts + high strength)
    for nd in G.nodes():
        if G.nodes[nd]["type"] not in ("PHONE", "PERSON"):
            continue
        deg = G.degree(nd)
        strength = G.nodes[nd].get("strength", 0)
        if deg >= 4 and strength >= 15:
            flags.append(dict(entity_id=nd, flag="high_traffic",
                              note="Unusually connected node with heavy interaction volume"))
    # 3) Articulation point = bridge controlling network connectivity. If a
    #    PERSON, likely a controller/coordinator even if "quiet".
    try:
        arts = set(nx.articulation_points(G))
    except Exception:
        arts = set()
    for nd in arts:
        if G.nodes[nd]["type"] == "PERSON" and G.nodes[nd].get("strength", 0) >= 5:
            flags.append(dict(entity_id=nd, flag="bridge_node",
                              note="Articulation point — removing this node fragments the network"))
    return flags


def analyze(entities, edges) -> dict:
    """Full graph analysis -> everything the dashboard needs."""
    G = build_graph(entities, edges)
    add_centrality(G)
    community_label(G)
    anomalies = detect_anomalies(G)

    # Composite threat score: normalize each measure then blend.
    # Balance across dimensions so no single signal (money flow) dominates:
    #   betweenness + eigenvector = structural influence (bridges + hidden controller)
    #   strength + degree = activity level
    norm = {}
    for m in ("betweenness", "degree", "strength", "eigenvector"):
        vals = [G.nodes[n][m] for n in G.nodes()]
        mx = max(vals) if vals else 1
        norm[m] = {n: (v / mx if mx else 0) for n, v in
                   ((n, G.nodes[n][m]) for n in G.nodes())}
    for nd in G.nodes():
        threat = (0.30 * norm["betweenness"][nd]
                  + 0.25 * norm["eigenvector"][nd]
                  + 0.20 * norm["strength"][nd]
                  + 0.25 * norm["degree"][nd])
        n_flags = sum(1 for a in anomalies if a["entity_id"] == nd)
        threat += 0.03 * n_flags
        G.nodes[nd]["threat"] = round(min(threat, 1.0), 4)

    # Top influencers = highest threat among PERSON/ACCOUNT/PHONE (drop pure LOC/VEHICLE)
    ranking = sorted(
        [G.nodes[n] for n in G.nodes() if G.nodes[n]["type"] in ("PERSON", "ACCOUNT", "PHONE")],
        key=lambda e: e["threat"], reverse=True,
    )[:25]

    # ---- Role classification for the top influencer set (the "who's who"
    # answer investigators want). Uses the flags + centrality to infer role.
    try:
        arts = set(nx.articulation_points(G))
    except Exception:
        arts = set()
    flag_by_id = defaultdict(list)
    for a in anomalies:
        flag_by_id[a["entity_id"]].append(a["flag"])

    # Net money flow per node: + = receiver (money sink), - = sender (funnel).
    # Computed in extraction (directed edges), propagated onto node attrs.
    net_money = {nd: float(G.nodes[nd].get("net_money", 0)) for nd in G.nodes()}

    roles = []
    # Find clear financial outliers among bridge people (the true launderer
    # consolidates an order-of-magnitude more money than everyone else doing
    # small "cuts"). Only these get the financier role.
    bridge_person_nets = [net_money[rid] for rid in G.nodes()
                          if rid in arts and G.nodes[rid]["type"] == "PERSON"
                          and net_money[rid] < 0]
    strong_sender_thresh = 0.0
    if bridge_person_nets:
        # 3x the median negative outflow = a genuine consolidation outlier
        neg_sorted = sorted(bridge_person_nets)
        if neg_sorted:
            strong_sender_thresh = 3 * (-neg_sorted[len(neg_sorted)//2])

    for e in ranking:
        rid, rtype, rv = e["id"], e["type"], e["value"]
        fl = flag_by_id.get(rid, [])
        is_bridge = rid in arts
        net = net_money.get(rid, 0)
        score = e.get("threat", 0)
        if rtype == "ACCOUNT":
            # accounts are shell/laundering vehicles, not "people roles"
            role = "financier" if score >= 0.3 else "account"
        elif ("money_funnel" in fl) and rtype != "PERSON":
            role = "financier"
        elif is_bridge and net <= -strong_sender_thresh and strong_sender_thresh > 0 \
                and net < -50 and score >= 0.10:
            # genuine consolidation outlier (money launderer)
            role = "financier"
        elif is_bridge and net > 0 and score >= 0.10:
            # PERSON who is a bridge AND a net money receiver => the controller
            role = "kingpin"
        elif is_bridge and score >= 0.10:
            role = "lieutenant"
        elif score >= 0.05:
            role = "associate"
        else:
            role = "node"
        roles.append(dict(id=rid, name=rv, type=rtype, threat=round(score, 4),
                          role=role))

    # Ensure the single top controller is surfaced: if a clear money-sink
    # bridge PERSON exists, designate the highest-threat one as kingpin.
    sink_bridges = [r for r in roles
                    if r["type"] == "PERSON" and r["id"] in arts
                    and net_money.get(r["id"], 0) > 0 and r["threat"] >= 0.10]
    if sink_bridges:
        target = max(sink_bridges, key=lambda r: r["threat"])
        for r in roles:
            r["role"] = "kingpin" if r["id"] == target["id"] else (
                "lieutenant" if r["role"] == "kingpin" else r["role"])

    # Communities ranked by aggregate threat (gangs)
    comms = defaultdict_comm(G)

    nodes_out = []
    for nd in G.nodes():
        n = dict(G.nodes[nd]); n["id"] = nd; nodes_out.append(n)
    edges_out = []
    for u, v, d in G.edges(data=True):
        edges_out.append(dict(source=u, target=v, weight=round(d["weight"], 3),
                              kinds=d.get("kinds", [])))
    return dict(
        nodes=nodes_out, edges=edges_out,
        top_influencers=roles,
        communities=comms,
        anomalies=[dict(id=a["entity_id"], flag=a["flag"], note=a["note"])
                   for a in anomalies],
        stats=dict(n_nodes=G.number_of_nodes(), n_edges=G.number_of_edges(),
                   n_communities=len(comms), backbone=3),
    )


def defaultdict_comm(G: nx.Graph) -> list[dict]:
    from collections import defaultdict
    agg = defaultdict(lambda: dict(threat=0.0, size=0, members_top=[]))
    for nd in G.nodes():
        c = G.nodes[nd].get("community", 0)
        agg[c]["threat"] += G.nodes[nd].get("threat", 0)
        agg[c]["size"] += 1
    out = []
    for c, v in agg.items():
        out.append(dict(community=int(c), size=v["size"],
                        threat=round(v["threat"], 3),
                        members=[]))
    out.sort(key=lambda x: x["threat"], reverse=True)
    return out