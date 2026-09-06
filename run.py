"""
Quick launcher. Usage:
  python run.py data      # regenerate synthetic dataset
  python run.py pipeline  # run extraction + analytics
  python run.py verify    # end-to-end verification (seeks the planted gang+kingpin)
  python run.py serve     # start FastAPI dashboard server on :8000
  python run.py all       # data -> pipeline -> verify
"""
import sys, subprocess

def sh(*a):
    print(">", " ".join(a), flush=True)
    return subprocess.call(list(a))

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    py = sys.executable
    if cmd == "data":
        sh(py, "scripts/gen_data.py")
    elif cmd == "pipeline":
        sh(py, "-m", "app.pipeline")
    elif cmd == "verify":
        sh(py, "-m", "app.verify")
    elif cmd == "serve":
        sh(py, "-m", "uvicorn", "app.api:app", "--host", "127.0.0.1", "--port", "8000", "--reload")
    elif cmd == "all":
        sh(py, "scripts/gen_data.py")
        sh(py, "-m", "app.pipeline")
        sh(py, "-m", "app.verify")
    else:
        print(__doc__)

if __name__ == "__main__":
    main()