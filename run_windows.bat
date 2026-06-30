@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Sample Detective - Local RAG / LLM
echo ============================================================

set "OLLAMA_MODEL=llama3.2:3b"

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

where ollama >nul 2>nul
if errorlevel 1 (
    echo Ollama wurde nicht gefunden. Die App startet trotzdem ohne lokale LLM-Antworten.
    echo Optional: Ollama installieren und dieses Script danach erneut ausfuehren.
) else (
    echo Pruefe Ollama-Modell %OLLAMA_MODEL% ...
    ollama list | findstr /I /L /C:"%OLLAMA_MODEL%" >nul 2>nul
    if errorlevel 1 (
        echo Lade Ollama-Modell %OLLAMA_MODEL% ...
        ollama pull %OLLAMA_MODEL%
        if errorlevel 1 (
            echo Ollama-Modell konnte nicht geladen werden. Die App startet trotzdem.
            echo In der App kannst du "Ollama fuer freie RAG-Fragen nutzen" deaktivieren.
        )
    ) else (
        echo Ollama-Modell %OLLAMA_MODEL% ist bereits installiert.
    )
)

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
