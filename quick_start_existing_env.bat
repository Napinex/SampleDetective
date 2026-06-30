@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    python -m venv .venv
)
call ".venv\Scripts\activate.bat"
pip install -r requirements.txt
python ingest.py
python -m streamlit run app.py
pause
