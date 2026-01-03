# import_json_to_db.py
import os
import json

from app import app, DATA_FILE
from models import db, Show, Song, ChecklistItem


def import_from_json():
    if not os.path.exists(DATA_FILE):
        print(f"JSON-Datei '{DATA_FILE}' wurde nicht gefunden. Abbruch.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    shows_data = data.get("shows", [])

    with app.app_context():
        # Wir setzen die DB einmal komplett zurück
        db.drop_all()
        db.create_all()

        imported_count = 0

        for raw_show in shows_data:
            show_id = raw_show.get("id")

            # Stammdaten
            show = Show(
                id=show_id,  # gleiche ID wie im JSON
                name=raw_show.get("name", "") or "",
                artist=raw_show.get("artist", "") or "",
                date=raw_show.get("date", "") or "",
                venue_type=raw_show.get("venue_type", "") or "",
                genre=raw_show.get("genre", "") or "",
                rig_type=raw_show.get("rig_type", "") or "",
                regie=raw_show.get("regie", "") or "",
                veranstalter=raw_show.get("veranstalter", "") or "",
                vt_firma=raw_show.get("vt_firma", "") or "",
                technischer_leiter=raw_show.get("technischer_leiter", "") or "",
                notes=raw_show.get("notes", "") or "",
            )

            # Rig-Setup aus verschachtelter Struktur
            rig = raw_show.get("rig_setup") or {}
            show.rig_manufacturer = rig.get("manufacturer", "") or ""

            show.rig_spots = rig.get("spots", "") or ""
            show.rig_washes = rig.get("washes", "") or ""
            show.rig_beams = rig.get("beams", "") or ""
            show.rig_blinders = rig.get("blinders", "") or ""
            show.rig_strobes = rig.get("strobes", "") or ""

            show.rig_positions = rig.get("positions", "") or ""
            show.rig_notes = rig.get("notes", "") or ""

            show.power_main = rig.get("power_main", "") or ""
            show.power_light = rig.get("power_light", "") or ""
            show.power_sound = rig.get("power_sound", "") or ""
            show.power_video = rig.get("power_video", "") or ""
            show.power_foh = rig.get("power_foh", "") or ""
            show.power_other = rig.get("power_other", "") or ""

            # Songs / Szenen
            songs = raw_show.get("songs") or []
            for s in songs:
                song = Song(
                    order_index=s.get("order_index", 1) or 1,
                    name=s.get("name", "") or "",
                    mood=s.get("mood", "") or "",
                    colors=s.get("colors", "") or "",
                    movement_style=s.get("movement_style", "") or "",
                    eye_candy=s.get("eye_candy", "") or "",
                    special_notes=s.get("special_notes", "") or "",
                    general_notes=s.get("general_notes", "") or "",
                )
                show.songs.append(song)

            # Checklisten
            cl = raw_show.get("checklists") or {}
            for category in ("preproduction", "aufbau", "show"):
                items = cl.get(category) or []
                for item in items:
                    ci = ChecklistItem(
                        category=category,
                        text=item.get("text", "") or "",
                        done=bool(item.get("done", False)),
                    )
                    show.checklist_items.append(ci)

            db.session.add(show)
            imported_count += 1

        db.session.commit()
        print(f"Import abgeschlossen. {imported_count} Shows aus JSON in die Datenbank übernommen.")


if __name__ == "__main__":
    import_from_json()
