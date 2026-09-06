"""
FastAPI backend for the Criminal Network Analysis System.

Endpoints:
  GET  /          -> serve the dashboard HTML
  POST /analyze   -> run the full pipeline and return analytics JSON
  GET  /results   -> return the last-computed results
"""
from __future__ import annotations
import json, os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app import pipeline as pipe

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = Path(pipe.OUT_DIR) / "results.json"

app = FastAPI(title="Criminal Network Analysis System (SIH 2026)")


@app.get("/")
def root():
    return JSONResponse({
        "name": "Criminal Network Analysis System — SIH 2026",
        "endpoints": ["/analyze", "/results", "/health"],
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
    return p


@app.post("/analyze")
def analyze(dataset: str = "synthetic"):
    """Run extraction + graph analytics over the deployed dataset."""
    if dataset == "real":
        import sys
        sys.path.insert(0, str(ROOT))
        import scripts.run_real as rr  # noqa — writes results_real.json
        rr.main()
        return JSONResponse(json.loads(_results_for("real").read_text()))
    result = pipe.run()
    return JSONResponse(result)


@app.get("/results")
def results(dataset: str = "synthetic"):
    p = _results_for(dataset)
    if os.path.exists(p):
        return JSONResponse(json.loads(open(p, encoding="utf-8").read()))
    return JSONResponse({"error": "No results yet. POST /analyze first."}, status_code=404)


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