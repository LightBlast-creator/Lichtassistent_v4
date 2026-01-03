@echo off
REM Starte den Lichtdesign-Assistenten v2

REM In den Ordner wechseln, in dem dieses Skript liegt
cd /d "%~dp0"

REM Virtuelle Umgebung anlegen, falls noch nicht vorhanden
if not exist .venv (
    echo [INFO] Erstelle virtuelle Umgebung...
    py -m venv .venv
)

REM Virtuelle Umgebung aktivieren
call .venv\Scripts\activate

REM pip aktualisieren (optional, aber hilfreich)
py -m pip install --upgrade pip

REM Benötigte Pakete installieren
echo [INFO] Installiere Abhängigkeiten...
pip install -r requirements.txt

REM Flask-App starten
echo [INFO] Starte Lichtdesign-Assistent...
py app.py

REM Konsole offen halten, falls etwas schiefgeht
pause
