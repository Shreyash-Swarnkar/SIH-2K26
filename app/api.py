"""
FastAPI backend for the Criminal Network Analysis System.

Endpoints:
  GET  /          -> serve the dashboard HTML
  POST /analyze   -> run the full pipeline and return analytics JSON
  GET  /results   -> return the last-computed results
  GET  /node/{id} -> return node details + connection info & evidence
  GET  /subgraph/{id} -> return ego network (neighborhood) for an entity
  GET  /search    -> search entities by name/type
  GET  /datasets  -> list available datasets
  GET  /health    -> health check
"""
from __future__ import annotations
import json, os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app import pipeline as pipe

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = Path(pipe.OUT_DIR) / "results.json"

app = FastAPI(title="Criminal Network Analysis System (SIH 2026)")


@app.get("/")
def root():
    return JSONResponse({
        "name": "Criminal Network Analysis System — SIH 2026",
        "endpoints": ["/analyze", "/results", "/node/{id}", "/subgraph/{id}", "/search", "/datasets", "/health"],
    })


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/datasets")
def datasets():
    """List available datasets and their result availability."""
    known = ["real", "synthetic"]
    out = []
    for name in known:
        if name == "real":
            p = os.path.join(pipe.OUT_DIR, "results_real.json")
        else:
            p = os.path.join(pipe.OUT_DIR, "results.json")
        out.append({"name": name, "has_results": os.path.exists(p)})
    return out


def _results_for(dataset: str):
    if not dataset or dataset in ("synthetic", "default"):
        p = RESULTS_PATH
    else:
        p = os.path.join(pipe.OUT_DIR, f"results_{dataset}.json")
    return Path(p)


@app.post("/analyze")
def analyze(dataset: str = "synthetic"):
    """Run extraction + graph analytics over the deployed dataset."""
    if dataset == "real":
        import sys
        sys.path.insert(0, str(ROOT))
        import scripts.run_real as rr  # noqa — writes results_real.json
        rr.main()
        p = _results_for("real")
        return JSONResponse(json.loads(p.read_text(encoding="utf-8")))
    result = pipe.run()
    return JSONResponse(result)


@app.get("/results")
def results(dataset: str = "synthetic"):
    p = _results_for(dataset)
    if p.exists():
        return JSONResponse(json.loads(p.read_text(encoding="utf-8")))
    return JSONResponse({"error": "No results yet. POST /analyze first."}, status_code=404)


@app.get("/node/{node_id}")
def get_node(node_id: str, dataset: str = "synthetic"):
    """Get detailed connection info, neighbor list, and evidence trail for an entity."""
    p = _results_for(dataset)
    if not p.exists():
        raise HTTPException(status_code=404, detail="No results yet. Run analysis first.")
    data = json.loads(p.read_text(encoding="utf-8"))
    
    nodes_map = {n["id"]: n for n in data.get("nodes", [])}
    if node_id not in nodes_map:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found.")
    
    node = nodes_map[node_id]
    
    # Find all relations/edges involving node_id
    relations = data.get("relations", data.get("edges", []))
    connections = []
    for rel in relations:
        u, v = rel.get("u") or rel.get("source"), rel.get("v") or rel.get("target")
        if u == node_id or v == node_id:
            other_id = v if u == node_id else u
            other_node = nodes_map.get(other_id, {"id": other_id, "value": other_id, "type": "UNKNOWN"})
            connections.append({
                "neighbor_id": other_id,
                "neighbor_name": other_node.get("value", other_id),
                "neighbor_type": other_node.get("type", "UNKNOWN"),
                "neighbor_threat": other_node.get("threat", 0.0),
                "weight": rel.get("weight", 1.0),
                "kinds": rel.get("kinds", []),
                "evidence": rel.get("evidence", []),
                "directed": rel.get("directed", [])
            })
            
    return JSONResponse({
        "node": node,
        "connections_count": len(connections),
        "connections": sorted(connections, key=lambda x: x["weight"], reverse=True)
    })


@app.get("/subgraph/{node_id}")
def get_subgraph(node_id: str, depth: int = Query(1, ge=1, le=2), dataset: str = "synthetic"):
    """Get ego network subgraph (nodes and edges) up to specified depth around node_id."""
    p = _results_for(dataset)
    if not p.exists():
        raise HTTPException(status_code=404, detail="No results yet. Run analysis first.")
    data = json.loads(p.read_text(encoding="utf-8"))
    
    nodes_map = {n["id"]: n for n in data.get("nodes", [])}
    if node_id not in nodes_map:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found.")
    
    relations = data.get("relations", data.get("edges", []))
    
    visited_nodes = {node_id}
    current_layer = {node_id}
    
    for _ in range(depth):
        next_layer = set()
        for rel in relations:
            u, v = rel.get("u") or rel.get("source"), rel.get("v") or rel.get("target")
            if u in current_layer and v not in visited_nodes:
                visited_nodes.add(v)
                next_layer.add(v)
            elif v in current_layer and u not in visited_nodes:
                visited_nodes.add(u)
                next_layer.add(u)
        current_layer = next_layer
        
    sub_nodes = [nodes_map[nid] for nid in visited_nodes if nid in nodes_map]
    sub_edges = []
    for rel in relations:
        u, v = rel.get("u") or rel.get("source"), rel.get("v") or rel.get("target")
        if u in visited_nodes and v in visited_nodes:
            sub_edges.append(rel)
            
    return JSONResponse({
        "center_node": node_id,
        "depth": depth,
        "nodes": sub_nodes,
        "edges": sub_edges,
        "stats": {
            "n_nodes": len(sub_nodes),
            "n_edges": len(sub_edges)
        }
    })


@app.get("/search")
def search_entities(q: str = Query(..., min_length=2), dataset: str = "synthetic"):
    """Search entities by name or ID matching query string q."""
    p = _results_for(dataset)
    if not p.exists():
        raise HTTPException(status_code=404, detail="No results yet. Run analysis first.")
    data = json.loads(p.read_text(encoding="utf-8"))
    
    q_low = q.lower()
    matches = []
    for node in data.get("nodes", []):
        name = str(node.get("value", "")).lower()
        nid = str(node.get("id", "")).lower()
        ntype = str(node.get("type", "")).lower()
        if q_low in name or q_low in nid or q_low in ntype:
            matches.append(node)
            
    return JSONResponse({
        "query": q,
        "count": len(matches),
        "results": sorted(matches, key=lambda x: x.get("threat", 0), reverse=True)[:50]
    })


@app.get("/ui")
def ui():
    return FileResponse(ROOT / "app" / "dashboard.html")


@app.get("/cytoscape.min.js")
def cyjs():
    """Serve Cytoscape.js locally (no external CDN dependency — works offline)."""
    return FileResponse(ROOT / "app" / "cytoscape.min.js")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
