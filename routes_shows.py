
from flask import render_template, request, redirect, url_for, abort, send_file, session
from pathlib import Path
from flask import send_file
import werkzeug
import uuid
from app import app  # <-- WICHTIG: Flask-App importieren

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
import show_logic
from show_logic import (
    MANUFACTURERS,
    create_default_show,
    create_song,
    create_check_item,
    toggle_check_item,
    remove_show,
    remove_song_from_show,
    duplicate_show,
    find_show,
    save_data,
    sync_entire_show_to_db,
)

# -----------------------------------------------------------------------------#
# Dashboard
# -----------------------------------------------------------------------------#


@app.route("/", methods=["GET", "POST"])
def dashboard():
    # Login-Check: Nur eingeloggte User dürfen Dashboard sehen
    if not session.get('user'):
        return redirect(url_for('login'))

    """
    Dashboard: Shows anlegen und Übersicht.
    - Shows werden weiterhin in shows.json angelegt.
    - Jede Show wird zusätzlich in der SQLite-DB gespiegelt.
    """

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        artist = request.form.get("artist", "").strip()
        date = request.form.get("date", "").strip()
        venue_type = request.form.get("venue_type", "").strip()
        genre = request.form.get("genre", "").strip()
        rig_type = request.form.get("rig_type", "").strip()

        # 1) Wie bisher: Show als Dict anlegen + in JSON speichern
        show = create_default_show(
            name=name,
            artist=artist,
            date=date,
            venue_type=venue_type,
            genre=genre,
            rig_type=rig_type,
        )
        show_logic.shows.append(show)
        save_data()

        # 2) DB-Sync: Show in SQLite spiegeln
        sync_entire_show_to_db(show)

        return redirect(url_for("show_detail", show_id=show["id"]))

    # GET: Shows kommen weiterhin aus der JSON-Liste
    return render_template("index.html", shows=show_logic.shows)


# -----------------------------------------------------------------------------#
# Show-Details / Duplizieren / Löschen
# -----------------------------------------------------------------------------#


@app.route("/show/<int:show_id>/duplicate", methods=["POST"])
def duplicate_show_route(show_id: int):
    """Route: Show duplizieren und direkt zur neuen Show springen."""
    new_show = duplicate_show(show_id)
    if not new_show:
        return redirect(url_for("dashboard"))
    return redirect(url_for("show_detail", show_id=new_show["id"]))


@app.route("/show/<int:show_id>", methods=["GET"])
def show_detail(show_id: int):
    """
    Show-Detailseite: Stammdaten, Songs, Rig, Checklisten.
    Mit Tab-Logik: active_tab = meta | rig | songs
    """
    show = find_show(show_id)
    if not show:
        abort(404)

    # Aktiven Tab aus Query-Parameter lesen (Standard: meta/Stammdaten)
    active_tab = request.args.get("tab", "meta")

    # NOTE: POST handling for updates was removed in favor of dedicated
    # endpoints (e.g. /show/<id>/update_meta, /show/<id>/update_rig,
    # /show/<id>/add_song, /show/<id>/checklists/*). This keeps the
    # show_detail view read-only and simplifies authorization and testing.

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
    try:
        song_id = int(song_id_raw)
    except (TypeError, ValueError):
        return redirect(url_for("show_detail", show_id=show_id, tab="songs"))

    remove_song_from_show(show, song_id)
    save_data()
    sync_entire_show_to_db(show)

    return redirect(url_for("show_detail", show_id=show_id, tab="songs"))


@app.route("/show/<int:show_id>/update_song", methods=["POST"])
def update_song(show_id: int):
    """Song / Szene nachträglich bearbeiten (JSON + DB-Sync)."""
    show = find_show(show_id)
    if not show:
        abort(404)

    song_id_raw = request.form.get("song_id", "")
    try:
        song_id = int(song_id_raw)
    except (TypeError, ValueError):
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

    return redirect(url_for("show_detail", show_id=show_id, tab="songs"))


@app.route("/show/<int:show_id>/move_song", methods=["POST"])
def move_song(show_id: int):
    """Song in der Reihenfolge nach oben/unten verschieben (JSON + DB-Sync)."""
    show = find_show(show_id)
    if not show:
        abort(404)

    song_id_raw = request.form.get("song_id", "")
    direction = request.form.get("direction", "")

    try:
        song_id = int(song_id_raw)
    except (TypeError, ValueError):
        return redirect(url_for("show_detail", show_id=show_id, tab="songs"))

    songs_list = show.get("songs", [])
    index = None
    for i, s in enumerate(songs_list):
        if s.get("id") == song_id:
            index = i
            break

    if index is None:
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