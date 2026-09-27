"""
Quick launcher. Usage:
  python run.py install   # create venv + install all dependencies (run once)
  python run.py data      # regenerate synthetic dataset
  python run.py pipeline  # run extraction + analytics
  python run.py verify    # end-to-end verification (seeks the planted gang+kingpin)
  python run.py serve     # start FastAPI dashboard server on :8000
  python run.py all       # data -> pipeline -> verify
"""
import sys, subprocess, os, venv

def sh(*a):
    print(">", " ".join(a), flush=True)
    return subprocess.call(list(a))

def ensure_venv():
    """Create venv and install deps if not already done."""
    venv_dir = ".venv"
    if not os.path.isdir(venv_dir):
        print("[*] Creating virtual environment...")
        venv.create(venv_dir, with_pip=True)
    # Determine python executable inside venv
    if os.name == "nt":
        py = os.path.join(venv_dir, "Scripts", "python.exe")
        pip = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        py = os.path.join(venv_dir, "bin", "python")
        pip = os.path.join(venv_dir, "bin", "pip")
    # Upgrade pip and install requirements
    print("[*] Installing/upgrading dependencies...")
    sh(pip, "install", "--upgrade", "pip")
    sh(pip, "install", "-r", "requirements.txt")
    # Install spaCy model
    sh(py, "-m", "spacy", "download", "en_core_web_sm")
    return py

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if cmd == "install":
        ensure_venv()
        print("[*] Setup complete. You can now run: python run.py all")
        return

    # For all other commands, ensure venv exists and use its python
    py = ensure_venv()

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