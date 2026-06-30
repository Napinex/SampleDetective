@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Sample Detective - Local RAG / LLM
echo ============================================================

where python >nul 2>nul
if errorlevel 1 (
    echo Python wurde nicht gefunden. Bitte Python 3.10+ installieren.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo Erstelle virtuelle Umgebung ...
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Aktualisiere pip ...
python -m pip install --upgrade pip

echo Installiere Requirements ...
pip install -r requirements.txt

echo Pruefe Datenbestand ...
python validate_data.py
if errorlevel 1 (
    echo Fehler beim Datenbestand.
    pause
    exit /b 1
)

echo Baue RAG-Index neu ...
python ingest.py
if errorlevel 1 (
    echo Fehler beim Index-Aufbau.
    pause
    exit /b 1
)

echo Starte SampleSphere AI ...
python -m streamlit run app.py

pause
