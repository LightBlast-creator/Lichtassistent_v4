
import sys
from flask import Flask, session, redirect, url_for, flash, render_template, request
try:
    from flask_wtf import CSRFProtect
    _CSRF_AVAILABLE = True
except Exception:
    CSRFProtect = None
    _CSRF_AVAILABLE = False
import os
from sqlalchemy import inspect, text
from models import db

# Dieses Modul auch als "app" importierbar machen,
# selbst wenn es als Script gestartet wird (python app.py)
sys.modules["app"] = sys.modules.get(__name__)

# Flask-App
app = Flask(__name__, template_folder="templates")




from show_logic import shows, save_data

# Dashboard: Show creation form + show list
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    from show_logic import load_data
    load_data()
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Neue Show anlegen
        name = request.form.get('name', '').strip()
        artist = request.form.get('artist', '').strip()
        date = request.form.get('date', '').strip()
        venue_type = request.form.get('venue_type', '').strip()
        genre = request.form.get('genre', '').strip()
        rig_type = request.form.get('rig_type', '').strip()
        if name:
            from show_logic import _empty_rig_setup
            new_id = max([s['id'] for s in shows], default=0) + 1
            shows.append({
                'id': new_id,
                'name': name,
                'artist': artist,
                'date': date,
                'venue_type': venue_type,
                'genre': genre,
                'rig_type': rig_type,
                'rig_setup': _empty_rig_setup(),
            })
            save_data()
        return redirect(url_for('dashboard'))
    return render_template('index.html', shows=shows)

# Optional: /show_overview leitet auf / weiter (altes Routing)
@app.route('/show_overview')
def show_overview():
    return redirect(url_for('dashboard'))

# Logout-Route
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Du wurdest ausgeloggt.', 'info')
    return redirect(url_for('login'))


# SECRET_KEY für CSRF (unbedingt in Produktion sicher setzen, z.B. via ENV)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

# Upload-Limit für große PDF-Dateien (100 MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# Fehlerbehandlung für zu große Uploads
from flask import render_template
@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template('error.html', message='Die hochgeladene Datei ist zu groß (max. 100 MB). Bitte wähle eine kleinere Datei oder teile sie auf.'), 413

# CSRF Schutz initialisieren falls verfügbar; ansonsten Fallback
if _CSRF_AVAILABLE and CSRFProtect is not None:
    csrf = CSRFProtect()
    csrf.init_app(app)
else:
    # Wenn Flask-WTF nicht installiert ist, verhindern wir Template-Errors
    # indem wir eine leere `csrf_token()` Template-Funktion bereitstellen.
    def _empty_csrf_token():
        return ""

    @app.context_processor
    def _inject_csrf_token():
        return {"csrf_token": _empty_csrf_token}

    print("[WARN] Flask-WTF nicht installiert — CSRF deaktiviert. Installiere 'Flask-WTF' für Schutz.")

# Datenbank-Konfiguration (SQLite im Projektordner)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shows.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# DB an Flask-App binden
db.init_app(app)

# ---------------------------------------------------------------------------
# Einfache Migration: fehlende Spalten in bestehenden Tabellen nachziehen
# ---------------------------------------------------------------------------
with app.app_context():
    engine = db.engine
    inspector = inspect(engine)

    # Tabelle "shows" existiert bereits?
    if "shows" in inspector.get_table_names():
        existing_columns = [col["name"] for col in inspector.get_columns("shows")]

        # Neue Spalte ma3_sequence_id bei Bedarf hinzufügen
        if "ma3_sequence_id" not in existing_columns:
            with engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE shows "
                        "ADD COLUMN ma3_sequence_id INTEGER DEFAULT 101"
                    )
                )
                conn.commit()

    # Stellt sicher, dass alle Tabellen grundsätzlich existieren
    db.create_all()

# Domain-Logik / JSON-Handling laden
import show_logic  # noqa: F401

# Routen registrieren (inkl. MA3-Export)
from routes_shows import *  # noqa: F401, F403

# -----------------------------
# Login-Route und Authentifizierung
# -----------------------------
from flask import render_template, request, redirect, url_for, session, flash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Zugangsdaten: Admin / Admin123
        if username == 'Admin' and password == 'Admin123':
            session['user'] = username
            flash('Login erfolgreich!', 'success')
            return redirect(url_for('show_overview'))
        else:
            flash('Login fehlgeschlagen. Bitte überprüfe Benutzername und Passwort.', 'danger')
    return render_template('login.html')

## Dashboard-Route entfernt, ist jetzt in routes_shows.py

if __name__ == "__main__":
    app.run(debug=True)