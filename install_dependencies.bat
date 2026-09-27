@echo off
REM Install dependencies for Criminal Network Analysis System (Windows)

REM Create virtual environment if not exists
if not exist ".venv" (
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install Python dependencies from requirements.txt
pip install -r requirements.txt

REM Install spaCy and the English model
pip install spacy
python -m spacy download en_core_web_sm

echo All dependencies installed successfully.
pause