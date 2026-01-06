# <-- WICHTIG: Flask-App importieren
from app import app
from show_logic import find_show, MANUFACTURERS, save_data, sync_entire_show_to_db, remove_song_from_show, remove_show, create_check_item, create_song
# Übernahme der erkannten Cues als neue Szenen/Songs
import json
import html
@app.route("/show/<int:show_id>/import_cuelist_pdf_commit", methods=["POST"])
def import_cuelist_pdf_commit(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)
    cues_json = request.form.get("cues_json")
    print("[DEBUG] cues_json (raw):", cues_json)
    if not cues_json:
        return "Keine Cues erkannt oder übergeben! (Feld leer)", 400
    # Versuche HTML-Entities zu dekodieren (z.B. &quot; → ")
    cues_json_decoded = html.unescape(cues_json)
    print("[DEBUG] cues_json (decoded):", cues_json_decoded)
    try:
        cues = json.loads(cues_json_decoded)
    except Exception as e:
        return f"Fehler beim Parsen der Cues! ({e})<br><pre>{cues_json_decoded}</pre>", 400
    if not cues or not isinstance(cues, list):
        return f"Keine Cues erkannt oder übergeben!<br><pre>{cues_json_decoded}</pre>", 400
    # Füge Cues als neue Songs/Szenen hinzu
    if "songs" not in show:
        show["songs"] = []
    order_index = max([s.get("order_index", 0) for s in show["songs"]], default=0) + 1
    for cue in cues:
        show["songs"].append({
            "id": int(1e6) + order_index,  # Dummy-ID, damit keine Kollision
            "order_index": order_index,
            "name": f"{cue.get('scene') or ''} {cue.get('role') or ''}".strip(),
            "mood": "",
            "colors": "",
            "movement_style": "",
            "eye_candy": "",
            "special_notes": cue.get("text", ""),
            "general_notes": "",
        })
        order_index += 1
    save_data()
    sync_entire_show_to_db(show)
    return redirect(url_for("show_detail", show_id=show_id, tab="songs"))

from app import app  # <-- WICHTIG: Flask-App importieren
import io
from werkzeug.utils import secure_filename
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


import spacy
import pdfplumber
import re

@app.route("/show/<int:show_id>/import_cuelist_pdf", methods=["POST"])
def import_cuelist_pdf(show_id: int):
    # KI-gestützte Named Entity Recognition mit spaCy
    show = find_show(show_id)
    if not show:
        abort(404)
    file = request.files.get("pdf_file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return "Keine PDF-Datei hochgeladen!", 400
    pdf_bytes = file.read()
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    nlp = spacy.load('de_core_news_sm')
    doc = nlp(text)
    # spaCy-Entities für Rollen (nur PERSON-Entities als Namen)
    spacy_roles = set(ent.text for ent in doc.ents if ent.label_ == 'PER')
    roles = list(spacy_roles)
    # Debug-Ausgabe für spaCy-Entities
    print("[spaCy] Erkannte Rollen (nur Namen):", spacy_roles)

    # Szenen und Cues können wie bisher extrahiert werden, falls benötigt
    spacy_scenes = set(ent.text for ent in doc.ents if ent.label_ in ('ORG', 'LOC') and 'Szene' in ent.text)
    spacy_cues = [ent.text for ent in doc.ents if ent.label_ in ('MISC', 'EVENT')]
    print("[spaCy] Erkannte Szenen:", spacy_scenes)
    print("[spaCy] Erkannte Cues:", spacy_cues)

    # KI-gestützte Named Entity Recognition mit spaCy
    nlp = spacy.load('de_core_news_sm')
    doc = nlp(text)
    # spaCy-Entities für Rollen, Szenen, Cues sammeln
    spacy_roles = set()
    spacy_scenes = set()
    spacy_cues = []
    for ent in doc.ents:
        # Rollen: PERSON, Szenen: ORG oder spezielle Marker, Cues: MISC
        if ent.label_ == 'PER':
            spacy_roles.add(ent.text)
        elif ent.label_ in ('ORG', 'LOC') and 'Szene' in ent.text:
            spacy_scenes.add(ent.text)
        elif ent.label_ in ('MISC', 'EVENT'):
            spacy_cues.append(ent.text)
    cues = []
    # spaCy-Rollen zu den erkannten Rollen hinzufügen
    for r in spacy_roles:
        if r not in roles:
            roles.append(r)
    # spaCy-Szenen zu den erkannten Szenen hinzufügen
    for s in spacy_scenes:
        if s not in [c.get('scene') for c in cues]:
            cues.append({'scene': s, 'role': None, 'text': '', 'uncertain': True})
    # spaCy-Cues als unsichere Cues ergänzen
    for c in spacy_cues:
        cues.append({'scene': None, 'role': None, 'text': c, 'uncertain': True})

    # --- Parsing-Logik für Theaterstück ---
    # 1. Rollen extrahieren
    roles = []
    roles_section = re.search(r"Rollen:(.*?)(?:Ort:|Zeit:|Szene|\n\n)", text, re.DOTALL | re.IGNORECASE)
    if roles_section:
        for line in roles_section.group(1).splitlines():
            line = line.strip()
            if line:
                role = re.split(r"[\s\t\-–—:]+", line, 1)[0]
                if role and role.upper() == role:
                    roles.append(role)
                elif role:
                    roles.append(role.split()[0])
    # Fallback: Wenn spaCy keine Rollen erkennt, suche alle im Text mehrfach vorkommenden, großgeschriebenen Wörter (außer Satzanfänge und Stoppwörter)
    if not roles:
        from collections import Counter
        import string
        import spacy.lang.de.stop_words as stopwords_mod
        stopwords = set(stopwords_mod.STOP_WORDS)
        word_counter = Counter()
        lines = text.splitlines()
        for line in lines:
            words = re.findall(r"\b[A-ZÄÖÜß][a-zäöüß]+\b", line)
            # Ignoriere das erste Wort, wenn es am Satzanfang steht
            if words:
                if line and line[0].isupper():
                    words = words[1:] if len(words) > 1 else []
            for w in words:
                if w.lower() not in stopwords and len(w) > 1:
                    word_counter[w] += 1
        # Nur Wörter, die mindestens 2x vorkommen und keine Stoppwörter sind
        fallback_roles = [w for w, c in word_counter.items() if c >= 2]
        roles.extend(fallback_roles)


    # 2. Szenen und Cues extrahieren (verbesserte Logik)
    cues = []
    current_scene = None
    current_role = None
    current_text = []
    role_patterns = [re.compile(rf"^\s*{re.escape(role)}[\s:：-]*", re.IGNORECASE) for role in roles]
    marker_patterns = [re.compile(r"(Licht|Ton|Cue|Szene|Musik|Effekt|Sound)", re.IGNORECASE)]
    cue_number_pattern = re.compile(r"^\s*\d+[.:]?\s*")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Szenenwechsel
        if re.match(r"Szene ?\d+", line, re.IGNORECASE):
            if current_role and current_text:
                cues.append({"scene": current_scene, "role": current_role, "text": " ".join(current_text), "uncertain": False})
            current_scene = line
            current_role = None
            current_text = []
            continue
        # Rollenname am Zeilenanfang erkennen
        matched_role = None
        for idx, pat in enumerate(role_patterns):
            m = pat.match(line)
            if m:
                matched_role = roles[idx]
                break
        if matched_role:
            if current_role and current_text:
                cues.append({"scene": current_scene, "role": current_role, "text": " ".join(current_text), "uncertain": False})
            current_role = matched_role
            rest = line[m.end():].strip()
            current_text = [rest] if rest else []
            continue
        # Marker wie Licht, Ton, Cue, Musik, Effekt, Sound erkennen
        marker_found = any(pat.search(line) for pat in marker_patterns)
        cue_number_found = cue_number_pattern.match(line)
        # Unsichere Zuordnung: Zeile enthält Marker oder Cue-Nummer, aber keine Rolle
        if marker_found or cue_number_found:
            cues.append({"scene": current_scene, "role": None, "text": line, "uncertain": True})
            continue
        # Text zur aktuellen Rolle
        if current_role:
            current_text.append(line)
        else:
            # Zeile ohne erkennbare Rolle oder Marker: als unsicher markieren
            cues.append({"scene": current_scene, "role": None, "text": line, "uncertain": True})
    # Letzten Cue speichern
    if current_role and current_text:
        cues.append({"scene": current_scene, "role": current_role, "text": " ".join(current_text), "uncertain": False})

    return render_template("import_cuelist_pdf_preview.html", show=show, pdf_text=text, cues=cues, roles=roles)
from app import app  # <-- WICHTIG: Flask-App importieren
from flask import Blueprint
from flask import render_template, request, redirect, url_for, abort, send_file, session
from pathlib import Path
# PDF-Export nur für Cue-Liste (mit Lichtler-Marker)
from pdf_export_cuelist import build_cuelist_pdf

@app.route("/show/<int:show_id>/export_cuelist_pdf")
def export_cuelist_pdf(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)
    buffer, filename = build_cuelist_pdf(show)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )
import werkzeug
import uuid


# Regie-Ansicht: GET = anzeigen, POST = bearbeiten
@app.route("/show/<int:show_id>/regie", methods=["GET"])
def show_regie_view(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)
    songs = show.get("songs", [])
    return render_template("regie_view.html", show=show, songs=songs)

# Cue bearbeiten (Name, Regie-Notiz)
@app.route("/show/<int:show_id>/regie/update_cue", methods=["POST"])
def regie_update_cue(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)
    song_id = request.form.get("song_id", type=int)
    name = request.form.get("song_name", "").strip()
    special_notes = request.form.get("song_special_notes", "").strip()
    for song in show.get("songs", []):
        if song.get("id") == song_id:
            song["name"] = name
            song["special_notes"] = special_notes
            break
    save_data()
    return redirect(url_for("show_regie_view", show_id=show_id))

# Cue-Reihenfolge ändern
@app.route("/show/<int:show_id>/regie/move_cue", methods=["POST"])
def regie_move_cue(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)
    song_id = request.form.get("song_id", type=int)
    direction = request.form.get("direction")
    songs = show.get("songs", [])
    idx = next((i for i, s in enumerate(songs) if s.get("id") == song_id), None)
    if idx is not None:
        if direction == "up" and idx > 0:
            songs[idx], songs[idx-1] = songs[idx-1], songs[idx]
        elif direction == "down" and idx < len(songs)-1:
            songs[idx], songs[idx+1] = songs[idx+1], songs[idx]
        # Reihenfolge neu setzen
        for i, s in enumerate(songs, 1):
            s["order_index"] = i
        save_data()
    return redirect(url_for("show_regie_view", show_id=show_id))

# -----------------------------------------------------------------------------#
# Requisiten-Bilder Löschen
# -----------------------------------------------------------------------------#
@app.route("/show/<int:show_id>/delete_prop_image/<filename>", methods=["POST"])
def delete_prop_image(show_id: int, filename: str):
    show = find_show(show_id)
    if not show:
        abort(404)
    song_id = request.form.get("song_id", type=int)
    found = False
    # Nur aus dem angegebenen Song löschen
    if song_id:
        for song in show.get("songs", []):
            if song.get("id") == song_id and "prop_images" in song and filename in song["prop_images"]:
                song["prop_images"].remove(filename)
                found = True
                break
    # Fallback: altes Verhalten (falls noch in show.prop_images)
    if not found and "prop_images" in show and filename in show["prop_images"]:
        show["prop_images"].remove(filename)
        found = True
    if found:
        save_data()
        try:
            (Path(app.root_path) / "static" / "props" / filename).unlink(missing_ok=True)
        except Exception:
            pass
    return redirect(url_for("show_detail", show_id=show_id, tab="props", song_id=song_id if song_id else None))

# -----------------------------------------------------------------------------#
# Requisiten-Bilder Upload/Entfernen
# -----------------------------------------------------------------------------#


# Neue Route: Bild gezielt einem Song zuordnen
@app.route("/show/<int:show_id>/upload_prop_image", methods=["POST"])
def upload_prop_image(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)
    song_id = request.form.get("song_id", type=int)
    file = request.files.get("prop_image")
    if file and file.filename and song_id:
        ext = werkzeug.utils.secure_filename(file.filename).rsplit(".", 1)[-1].lower()
        fname = f"{show_id}_{uuid.uuid4().hex[:8]}.{ext}"
        save_path = Path(app.root_path) / "static" / "props" / fname
        file.save(str(save_path))
        # Bild dem Song zuordnen
        for song in show.get("songs", []):
            if song.get("id") == song_id:
                song.setdefault("prop_images", []).append(fname)
                break
        save_data()
        return redirect(url_for("show_detail", show_id=show_id, tab="props"))
    # Fallback: altes Verhalten (falls kein Song gewählt)
    if file and file.filename:

        show["prop_images"].remove(filename)
        found = True
    if found:
        save_data()
        try:
            (Path(app.root_path) / "static" / "props" / filename).unlink(missing_ok=True)
        except Exception:
            pass
    return redirect(url_for("show_detail", show_id=show_id, tab="props"))
from flask import render_template, request, redirect, url_for, abort, send_file, session
from pathlib import Path
from flask import send_file

from models import db, Show as ShowModel, ContactPersonModel
from pdf_export import build_show_report_pdf, build_techrider_pdf

import ma3_export  # MA3-Exportmodul
from app import app  # Flask-App-Instanz

import math
def import_cuelist_pdf(show_id: int):
    import spacy
    import pdfplumber

    show = find_show(show_id)
    if not show:
        abort(404)
    file = request.files.get("pdf_file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return "Keine PDF-Datei hochgeladen!", 400
    pdf_bytes = file.read()
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    # --- Parsing-Logik für Theaterstück ---
    cues = []
    # 1. Rollen extrahieren
    roles = []
    roles_section = re.search(r"Rollen:(.*?)(?:Ort:|Zeit:|Szene|\n\n)", text, re.DOTALL | re.IGNORECASE)
    if roles_section:
        for line in roles_section.group(1).splitlines():
            line = line.strip()
            if line:
                role = re.split(r"[\s\t\-–—:]+", line, 1)[0]
                if role and role.upper() == role:
                    roles.append(role)
                elif role:
                    roles.append(role.split()[0])
    # Fallback: alle Wörter in Großbuchstaben am Zeilenanfang als Rollenname
    if not roles:
        for line in text.splitlines():
            if re.match(r"^[A-ZÄÖÜß]{2,}( |$)", line):
                role = line.split()[0]
                if role not in roles:
                    roles.append(role)

    # KI-gestützte Named Entity Recognition mit spaCy
    nlp = spacy.load('de_core_news_sm')
    doc = nlp(text)
    # spaCy-Entities für Rollen, Szenen, Cues sammeln
    spacy_roles = set()
    spacy_scenes = set()
    spacy_cues = []
    for ent in doc.ents:
        # Rollen: PERSON, Szenen: ORG oder spezielle Marker, Cues: MISC
        if ent.label_ == 'PER':
            spacy_roles.add(ent.text)
        elif ent.label_ in ('ORG', 'LOC') and 'Szene' in ent.text:
            spacy_scenes.add(ent.text)
        elif ent.label_ in ('MISC', 'EVENT'):
            spacy_cues.append(ent.text)
    # spaCy-Rollen zu den erkannten Rollen hinzufügen
    for r in spacy_roles:
        if r not in roles:
            roles.append(r)
    # spaCy-Szenen zu den erkannten Szenen hinzufügen
    for s in spacy_scenes:
        if s not in [c.get('scene') for c in cues]:
            cues.append({'scene': s, 'role': None, 'text': '', 'uncertain': True})
    # spaCy-Cues als unsichere Cues ergänzen
    for c in spacy_cues:
        cues.append({'scene': None, 'role': None, 'text': c, 'uncertain': True})
    # Debug-Ausgabe für spaCy-Entities
    print("[spaCy] Erkannte Rollen:", spacy_roles)
    print("[spaCy] Erkannte Szenen:", spacy_scenes)
    print("[spaCy] Erkannte Cues:", spacy_cues)
@app.route("/show/<int:show_id>", methods=["GET"])
def show_detail(show_id: int):
    """
    Show-Detailseite: Stammdaten, Songs, Rig, Checklisten.
    Mit Tab-Logik: active_tab = meta | rig | songs | regie
    """
    show = find_show(show_id)
    if not show:
        abort(404)

    # Aktiven Tab aus Query-Parameter lesen (Standard: meta/Stammdaten)
    active_tab = request.args.get("tab", "meta")

    # Regie-Tab: keine Editiermöglichkeiten, nur Anzeige der Cue-Liste mit Regie-Infos
    # (Die Logik für die Anzeige ist im Template show_regie_tab.html)

    # ---------------- GET: Rig-Power-Berechnung ----------------
    rig = show.get("rig_setup", {}) or {}

    def _to_float(value):
        try:
            s = str(value).strip().replace(",", ".")
            return float(s) if s else 0.0
        except Exception:
            return 0.0

    # Leistung aus den "Watt gesamt"-Feldern der Gerätegruppen
    # If repeatable items exist (e.g. rig.spots_items), include their watt*count as well.
    prefixes = ("spots", "washes", "beams", "blinders", "strobes")
    total_watt = 0.0
    for prefix in prefixes:
        items = rig.get(f"{prefix}_items")
        if items:
            for it in items:
                w = _to_float(it.get("watt") or 0)
                try:
                    cnt = int((it.get("count") or "0").strip() or 0)
                except Exception:
                    cnt = 0
                total_watt += w * cnt
        else:
            total_watt += _to_float(rig.get(f"watt_{prefix}"))

    # Summe der Strom-Einträge Main/Light/...
    power_fields = ["power_main", "power_light", "power_sound", "power_video", "power_foh", "power_other"]
    total_power = sum(_to_float(rig.get(f)) for f in power_fields)

    rig_power_summary = None
    if total_watt > 0 or total_power > 0:
        total_kw = None
        apparent_kva = None
        current_1ph = None
        current_3ph = None
        cos_phi = None

        if total_watt > 0:
            cos_phi = 0.95  # angenommener Leistungsfaktor
            total_kw = total_watt / 1000.0
            apparent_kva = total_kw / cos_phi
            # 1~ 230 V
            current_1ph = total_watt / (230.0 * cos_phi)
            # 3~ 400 V symmetrisch: P = sqrt(3) * U * I * cos φ
            current_3ph = total_watt / (math.sqrt(3.0) * 400.0 * cos_phi)

        rig_power_summary = {
            "total_watt": total_watt if total_watt > 0 else None,
            "total_kw": total_kw,
            "apparent_kva": apparent_kva,
            "current_1ph": current_1ph,
            "current_3ph": current_3ph,
            "cos_phi": cos_phi,
            "total_power": total_power if total_power > 0 else None,
        }

    # Kontakte (aus der DB) holen
    db_show = ShowModel.query.get(show_id)
    contacts = db_show.contacts if db_show else []

    # Optional: restore values set by POST handlers (stored in session)
    restore_scroll = session.pop('restore_scroll', None)
    restore_tab = session.pop('restore_tab', None)

    # Template bekommt Show + Herstellerliste + aktiven Tab + Kontakte
    return render_template(
        "show_detail.html",
        show=show,
        manufacturers=MANUFACTURERS,
        active_tab=active_tab,
        rig_power_summary=rig_power_summary,
        contacts=contacts,
        restore_scroll=restore_scroll,
        restore_tab=restore_tab,
    )


# -----------------------------------------------------------------------------#
# DEDIZIERTE POST-ROUTEN (statt action-switch im show_detail)
# -----------------------------------------------------------------------------#

# -----------------------------------------------------------------------------#
# Video Upload/Delete
# -----------------------------------------------------------------------------#

@app.route("/show/<int:show_id>/upload_video", methods=["POST"])
def upload_video(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)
    if "videos" not in show:
        show["videos"] = []
    file = request.files.get("video")
    if file and file.filename:
        ext = werkzeug.utils.secure_filename(file.filename).rsplit(".", 1)[-1].lower()
        fname = f"{show_id}_{uuid.uuid4().hex[:8]}.{ext}"
        save_path = Path(app.root_path) / "static" / "videos" / fname
        file.save(str(save_path))
        show["videos"].append(fname)
        save_data()
    return redirect(url_for("show_detail", show_id=show_id, tab="videos"))

@app.route("/show/<int:show_id>/delete_video/<filename>", methods=["POST"])
def delete_video(show_id: int, filename: str):
    show = find_show(show_id)
    if not show:
        abort(404)
    if "videos" in show and filename in show["videos"]:
        show["videos"].remove(filename)
        save_data()
        # Datei auch aus dem Dateisystem löschen
        try:
            (Path(app.root_path) / "static" / "videos" / filename).unlink(missing_ok=True)
        except Exception:
            pass
    return redirect(url_for("show_detail", show_id=show_id, tab="videos"))


@app.route("/show/<int:show_id>/update_meta", methods=["POST"])
def update_meta(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)

    show["name"] = request.form.get("name", "").strip() or show.get("name", "")
    show["artist"] = request.form.get("artist", "").strip()
    show["date"] = request.form.get("date", "").strip()
    show["venue_type"] = request.form.get("venue_type", "").strip()
    show["genre"] = request.form.get("genre", "").strip()
    show["rig_type"] = request.form.get("rig_type", "").strip()
    show["regie"] = request.form.get("regie", "").strip()
    show["veranstalter"] = request.form.get("veranstalter", "").strip()
    show["vt_firma"] = request.form.get("vt_firma", "").strip()
    show["technischer_leiter"] = request.form.get("technischer_leiter", "").strip()
    show["notes"] = request.form.get("notes", "").strip()

    seq_raw = (request.form.get("ma3_sequence_id") or "").strip()
    if seq_raw:
        try:
            show["ma3_sequence_id"] = int(seq_raw)
        except ValueError:
            show["ma3_sequence_id"] = 101
    else:
        show["ma3_sequence_id"] = 101

    save_data()
    sync_entire_show_to_db(show)

    return redirect(url_for("show_detail", show_id=show_id, tab="meta"))


@app.route("/show/<int:show_id>/update_rig", methods=["POST"])
def update_rig(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)

    rig = show.setdefault("rig_setup", {})

    rig["main_brand"] = request.form.get("rig_main_brand", "").strip()

    # Gruppiertes Auslesen der Felder (Spots/Washes/Beams/Blinders/Strobes)
    for prefix in ("spots", "washes", "beams", "blinders", "strobes"):
        counts = request.form.getlist(f"rig_{prefix}__count[]")
        manufacturers = request.form.getlist(f"rig_{prefix}__manufacturer[]")
        models = request.form.getlist(f"rig_{prefix}__model[]")
        modes = request.form.getlist(f"rig_{prefix}__mode[]")
        universes = request.form.getlist(f"rig_{prefix}__universe[]")
        addresses = request.form.getlist(f"rig_{prefix}__address[]")
        watts = request.form.getlist(f"rig_{prefix}__watt[]")
        phases = request.form.getlist(f"rig_{prefix}__phase[]")

        items = []
        for i, c in enumerate(counts):
            item = {
                "count": c.strip() if c else "",
                "manufacturer": (manufacturers[i].strip() if i < len(manufacturers) else ""),
                "model": (models[i].strip() if i < len(models) else ""),
                "mode": (modes[i].strip() if i < len(modes) else ""),
                "universe": (universes[i].strip() if i < len(universes) else ""),
                "address": (addresses[i].strip() if i < len(addresses) else ""),
                "watt": (watts[i].strip() if i < len(watts) else ""),
                "phase": (phases[i].strip() if i < len(phases) else ""),
            }
            items.append(item)
        if items:
            rig[f"{prefix}_items"] = items
        else:
            # Backwards-compatible single-value fields
            rig[f"{prefix}"] = request.form.get(f"rig_{prefix}", "").strip()
            rig[f"manufacturer_{prefix}"] = request.form.get(f"rig_manufacturer_{prefix}", "").strip()
            rig[f"universe_{prefix}"] = request.form.get(f"rig_universe_{prefix}", "").strip()
            rig[f"address_{prefix}"] = request.form.get(f"rig_address_{prefix}", "").strip()
            rig[f"watt_{prefix}"] = request.form.get(f"rig_watt_{prefix}", "").strip()
            rig[f"phase_{prefix}"] = request.form.get(f"rig_phase_{prefix}", "").strip()

    rig["positions"] = request.form.get("rig_positions", "").strip()
    rig["notes"] = request.form.get("rig_notes", "").strip()

    rig["power_main"] = request.form.get("rig_power_main", "").strip()
    rig["power_light"] = request.form.get("rig_power_light", "").strip()
    rig["power_sound"] = request.form.get("rig_power_sound", "").strip()
    rig["power_video"] = request.form.get("rig_power_video", "").strip()
    rig["power_foh"] = request.form.get("rig_power_foh", "").strip()
    rig["power_other"] = request.form.get("rig_power_other", "").strip()


    # Custom Devices (user-defined lamps)
    custom_counts = request.form.getlist("custom_devices__count[]")
    custom_names = request.form.getlist("custom_devices__name[]")
    custom_models = request.form.getlist("custom_devices__model[]")
    custom_modes = request.form.getlist("custom_devices__mode[]")
    custom_manufacturers = request.form.getlist("custom_devices__manufacturer[]")
    custom_universes = request.form.getlist("custom_devices__universe[]")
    custom_addresses = request.form.getlist("custom_devices__address[]")
    custom_watts = request.form.getlist("custom_devices__watt[]")
    custom_phases = request.form.getlist("custom_devices__phase[]")

    custom_devices = []
    for i in range(len(custom_counts)):
        # Nur speichern, wenn mindestens Name oder Hersteller oder Anzahl ausgefüllt ist
        if (
            (custom_counts[i] and custom_counts[i].strip()) or
            (custom_names[i] and custom_names[i].strip()) or
            (custom_manufacturers[i] and custom_manufacturers[i].strip())
        ):
            custom_devices.append({
                "count": custom_counts[i].strip() if i < len(custom_counts) else "",
                "name": custom_names[i].strip() if i < len(custom_names) else "",
                "manufacturer": custom_manufacturers[i].strip() if i < len(custom_manufacturers) else "",
                "model": custom_models[i].strip() if i < len(custom_models) else "",
                "mode": custom_modes[i].strip() if i < len(custom_modes) else "",
                "universe": custom_universes[i].strip() if i < len(custom_universes) else "",
                "address": custom_addresses[i].strip() if i < len(custom_addresses) else "",
                "watt": custom_watts[i].strip() if i < len(custom_watts) else "",
                "phase": custom_phases[i].strip() if i < len(custom_phases) else "",
            })
    rig["custom_devices"] = custom_devices

    save_data()
    sync_entire_show_to_db(show)

    return redirect(url_for("show_detail", show_id=show_id, tab="rig"))


@app.route("/show/<int:show_id>/add_song", methods=["POST"])
def add_song_route(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)

    name = request.form.get("song_name", "").strip()
    mood = request.form.get("song_mood", "").strip()
    colors = request.form.get("song_colors", "").strip()
    movement_style = request.form.get("song_movement_style", "").strip()
    eye_candy = request.form.get("song_eye_candy", "").strip()
    special_notes = request.form.get("song_special_notes", "").strip()
    general_notes = request.form.get("song_general_notes", "").strip()

    create_song(
        show=show,
        name=name,
        mood=mood,
        colors=colors,
        movement_style=movement_style,
        eye_candy=eye_candy,
        special_notes=special_notes,
        general_notes=general_notes,
    )
    save_data()
    sync_entire_show_to_db(show)

    return redirect(url_for("show_detail", show_id=show_id, tab="songs"))


@app.route("/show/<int:show_id>/checklists/add", methods=["POST"])
def add_check_item_route(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)

    category = request.form.get("category", "")
    text = request.form.get("text", "").strip()
    if category in ("preproduction", "aufbau", "show") and text:
        create_check_item(show, category, text)
        save_data()
        sync_entire_show_to_db(show)

    return redirect(url_for("show_detail", show_id=show_id, tab="meta") + "#checklists")


@app.route("/show/<int:show_id>/checklists/toggle", methods=["POST"])
def toggle_check_item_route(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)

    category = request.form.get("category", "")
    item_id_raw = request.form.get("item_id", "")
    try:
        item_id = int(item_id_raw)
    except (TypeError, ValueError):
        item_id = None

    if category in ("preproduction", "aufbau", "show") and item_id is not None:
        toggle_check_item(show, category, item_id)
        save_data()
        sync_entire_show_to_db(show)

    return redirect(url_for("show_detail", show_id=show_id, tab="meta") + "#checklists")


@app.route("/show/<int:show_id>/checklists/update", methods=["POST"])
def update_check_item_route(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)

    category = request.form.get("category", "")
    item_id_raw = request.form.get("item_id", "")
    text = request.form.get("text", "").strip()
    try:
        item_id = int(item_id_raw)
    except (TypeError, ValueError):
        item_id = None

    if (
        category in ("preproduction", "aufbau", "show")
        and item_id is not None
        and "checklists" in show
        and isinstance(show["checklists"], dict)
    ):
        items = show["checklists"].get(category, [])
        for item in items:
            if item.get("id") == item_id:
                item["text"] = text
                break
        save_data()
        sync_entire_show_to_db(show)

    return redirect(url_for("show_detail", show_id=show_id, tab="meta") + "#checklists")


@app.route("/show/<int:show_id>/checklists/delete", methods=["POST"])
def delete_check_item_route(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)

    category = request.form.get("category", "")
    item_id_raw = request.form.get("item_id", "")
    try:
        item_id = int(item_id_raw)
    except (TypeError, ValueError):
        item_id = None

    if (
        category in ("preproduction", "aufbau", "show")
        and item_id is not None
        and "checklists" in show
        and isinstance(show["checklists"], dict)
    ):
        items = show["checklists"].get(category, [])
        items = [i for i in items if i.get("id") != item_id]
        show["checklists"][category] = items
        save_data()
        sync_entire_show_to_db(show)

    return redirect(url_for("show_detail", show_id=show_id, tab="meta") + "#checklists")



@app.route("/show/<int:show_id>/delete", methods=["POST"])
def delete_show(show_id: int):
    """Route: komplette Show löschen (JSON + DB)."""
    show = find_show(show_id)
    if not show:
        abort(404)


    # JSON
    remove_show(show_id)
    save_data()

    # DB
    try:
        db_show = ShowModel.query.get(show_id)
        if db_show:
            db.session.delete(db_show)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[DB] Fehler beim Löschen der Show {show_id}: {e}")

    # Synchronisiere die in-memory-Liste shows nach DB-Löschung
    from show_logic import load_data
    load_data()

    return redirect(url_for("dashboard"))


# -----------------------------------------------------------------------------#
# Song-Routen
# -----------------------------------------------------------------------------#


@app.route("/show/<int:show_id>/delete_song", methods=["POST"])
def delete_song(show_id: int):
    """Route: einzelne Szene/Song aus Show löschen (JSON + DB-Sync)."""
    show = find_show(show_id)
    if not show:
        abort(404)

    song_id_raw = request.form.get("song_id", "")
    from_regie = request.form.get("from_regie")
    try:
        song_id = int(song_id_raw)
    except (TypeError, ValueError):
        if from_regie:
            return redirect(url_for("show_regie_view", show_id=show_id))
        return redirect(url_for("show_detail", show_id=show_id, tab="songs"))

    remove_song_from_show(show, song_id)
    save_data()
    sync_entire_show_to_db(show)

    if from_regie:
        return redirect(url_for("show_regie_view", show_id=show_id))
    return redirect(url_for("show_detail", show_id=show_id, tab="songs"))


@app.route("/show/<int:show_id>/update_song", methods=["POST"])
def update_song(show_id: int):
    """Song / Szene nachträglich bearbeiten (JSON + DB-Sync)."""
    show = find_show(show_id)
    if not show:
        abort(404)

    song_id_raw = request.form.get("song_id", "")
    from_regie = request.form.get("from_regie")
    try:
        song_id = int(song_id_raw)
    except (TypeError, ValueError):
        if from_regie:
            return redirect(url_for("show_regie_view", show_id=show_id))
        return redirect(url_for("show_detail", show_id=show_id, tab="songs"))

    for song in show.get("songs", []):
        if song.get("id") == song_id:
            name = request.form.get("song_name", "").strip()
            if name:
                song["name"] = name

            song["mood"] = request.form.get("song_mood", "").strip()
            song["colors"] = request.form.get("song_colors", "").strip()
            song["movement_style"] = request.form.get("song_movement_style", "").strip()
            song["eye_candy"] = request.form.get("song_eye_candy", "").strip()
            song["special_notes"] = request.form.get("song_special_notes", "").strip()
            song["general_notes"] = request.form.get("song_general_notes", "").strip()
            break

    save_data()
    sync_entire_show_to_db(show)

    if from_regie:
        return redirect(url_for("show_regie_view", show_id=show_id))
    return redirect(url_for("show_detail", show_id=show_id, tab="songs"))


@app.route("/show/<int:show_id>/move_song", methods=["POST"])
def move_song(show_id: int):
    """Song in der Reihenfolge nach oben/unten verschieben (JSON + DB-Sync)."""
    show = find_show(show_id)
    if not show:
        abort(404)

    song_id_raw = request.form.get("song_id", "")
    direction = request.form.get("direction", "")
    from_regie = request.form.get("from_regie")

    try:
        song_id = int(song_id_raw)
    except (TypeError, ValueError):
        if from_regie:
            return redirect(url_for("show_regie_view", show_id=show_id))
        return redirect(url_for("show_detail", show_id=show_id, tab="songs"))

    songs_list = show.get("songs", [])
    index = None
    for i, s in enumerate(songs_list):
        if s.get("id") == song_id:
            index = i
            break

    if index is None:
        if from_regie:
            return redirect(url_for("show_regie_view", show_id=show_id))
        return redirect(url_for("show_detail", show_id=show_id, tab="songs"))

    if direction == "up" and index > 0:
        songs_list[index - 1], songs_list[index] = songs_list[index], songs_list[index - 1]
    elif direction == "down" and index < len(songs_list) - 1:
        songs_list[index + 1], songs_list[index] = songs_list[index], songs_list[index + 1]

    # Reihenfolge neu durchzählen
    for idx, s in enumerate(songs_list, start=1):
        s["order_index"] = idx

    show["songs"] = songs_list
    save_data()
    sync_entire_show_to_db(show)

    if from_regie:
        return redirect(url_for("show_regie_view", show_id=show_id))
    return redirect(url_for("show_detail", show_id=show_id, tab="songs"))


# -----------------------------------------------------------------------------#
# PDF-Routen
# -----------------------------------------------------------------------------#


@app.route("/show/<int:show_id>/export_pdf")
def export_show_pdf(show_id: int):
    """Erzeugt eine PDF-Datei mit Showdaten, Logo, Songs/Szenen, Rig und Checklisten."""
    show = find_show(show_id)
    if not show:
        return redirect(url_for("dashboard"))

    buffer, filename = build_show_report_pdf(show)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


@app.route("/show/<int:show_id>/export_techrider")
def export_techrider_pdf(show_id: int):
    """Erzeugt eine kompakte Tech-Rider-PDF mit Stammdaten, Kontakten, Setlist und Rig/Strom."""
    show = find_show(show_id)
    if not show:
        return redirect(url_for("dashboard"))

    buffer, filename = build_techrider_pdf(show)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


# -----------------------------------------------------------------------------#
# MA3-Export-Route
# -----------------------------------------------------------------------------#


@app.route("/show/<int:show_id>/export_ma3")
def export_ma3(show_id: int):
    """Erzeugt eine MA3-Lua-Datei für diese Show."""
    db_show = ShowModel.query.get_or_404(show_id)

    file_path = ma3_export.export_ma3_plugin_to_file(db_show)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=file_path.name,
        mimetype="text/x-lua",
    )


# -----------------------------------------------------------------------------#
# Contact CRUD
# -----------------------------------------------------------------------------#


@app.route("/show/<int:show_id>/contacts/add", methods=["POST"])
def add_contact(show_id: int):
    show = find_show(show_id)
    if not show:
        abort(404)

    role = request.form.get("role", "").strip()
    name = request.form.get("name", "").strip()
    company = request.form.get("company", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    notes = request.form.get("notes", "").strip()

    # Create DB entry
    try:
        contact = ContactPersonModel(
            show_id=show_id,
            role=role or "",
            name=name or None,
            company=company or None,
            phone=phone or None,
            email=email or None,
            notes=notes or None,
        )
        db.session.add(contact)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[DB] Fehler beim Anlegen des Kontakts: {e}")

    return redirect(url_for("show_detail", show_id=show_id, tab="contacts"))


@app.route("/show/<int:show_id>/contacts/<int:contact_id>/update", methods=["POST"])
def update_contact(show_id: int, contact_id: int):
    contact = ContactPersonModel.query.get(contact_id)
    if not contact or contact.show_id != show_id:
        abort(404)

    contact.role = request.form.get("role", "").strip() or contact.role
    contact.name = request.form.get("name", "").strip() or contact.name
    contact.company = request.form.get("company", "").strip() or contact.company
    contact.phone = request.form.get("phone", "").strip() or contact.phone
    contact.email = request.form.get("email", "").strip() or contact.email
    contact.notes = request.form.get("notes", "").strip() or contact.notes

    try:
        db.session.add(contact)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[DB] Fehler beim Aktualisieren des Kontakts: {e}")

    return redirect(url_for("show_detail", show_id=show_id, tab="contacts"))


@app.route("/show/<int:show_id>/contacts/<int:contact_id>/delete", methods=["POST"])
def delete_contact(show_id: int, contact_id: int):
    contact = ContactPersonModel.query.get(contact_id)
    if not contact or contact.show_id != show_id:
        abort(404)

    try:
        db.session.delete(contact)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[DB] Fehler beim Löschen des Kontakts: {e}")

    return redirect(url_for("show_detail", show_id=show_id, tab="contacts"))