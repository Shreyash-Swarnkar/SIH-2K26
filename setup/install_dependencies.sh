#!/usr/bin/env bash
set -e

# Activate virtual environment (create if not exists)
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/Scripts/activate

# Install Python dependencies from requirements.txt
pip install -r requirements.txt

# Install spaCy and the English model
pip install spacy
python -m spacy download en_core_web_sm

echo "All dependencies installed successfully."