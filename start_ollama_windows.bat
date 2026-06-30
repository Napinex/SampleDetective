@echo off
setlocal
echo Pruefe Ollama ...
where ollama >nul 2>nul
if errorlevel 1 (
    echo Ollama wurde nicht gefunden.
    echo Bitte installiere Ollama fuer Windows und oeffne danach PowerShell neu.
    pause
    exit /b 1
)

echo Starte Ollama Server im Hintergrund ...
start "" /min ollama serve

echo Optional: Kleines Modell laden ...
echo Wenn noch nicht vorhanden, fuehre aus:
echo ollama pull llama3.2:3b
pause
