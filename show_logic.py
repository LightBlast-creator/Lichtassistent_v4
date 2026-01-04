from typing import List, Dict, Optional
import json
import os
import copy

from models import db, Show as ShowModel, Song as SongModel, ChecklistItem as ChecklistItemModel

Show = Dict
Song = Dict

DATA_FILE = "shows.json"

shows: List[Show] = []
next_show_id: int = 1
next_song_id: int = 1
next_check_item_id: int = 1

# -----------------------------------------------------------------------------#
# KONFIGURATION: Hersteller-Liste
# -----------------------------------------------------------------------------#

MANUFACTURERS = [
    "Robe",
    "Clay Paky",
    "Martin Professional",
    "MA Lighting",
    "Ayrton",
    "GLP (German Light Products)",
    "ETC (Electronic Theatre Controls)",
    "Vari-Lite",
    "Astera",
    "SGM",
    "Chauvet Professional",
    "Cameo",
    "Elation Professional",
    "High End Systems",
    "JB-Lighting",
    "ARRI",
    "Litepanels",
    "Andere / Gemischt",
]

# -----------------------------------------------------------------------------#
# Helper-Funktionen / Defaults
# -----------------------------------------------------------------------------#


def _empty_rig_setup() -> Dict:
    """Standard-Structure für rig_setup, inkl. Hersteller- und Strom-Felder."""
    return {
        # globale Hersteller-Präferenz
        "main_brand": "",
        "manufacturer": "",  # altes Feld, bleibt für Kompatibilität

        # Spots
        "spots": "",
        "manufacturer_spots": "",
        "universe_spots": "",
        "address_spots": "",
        "watt_spots": "",
        "phase_spots": "",
        "models_spots": [],
        "modes_spots": [],

        # Washes
        "washes": "",
        "manufacturer_washes": "",
        "universe_washes": "",
        "address_washes": "",
        "watt_washes": "",
        "phase_washes": "",
        "models_washes": [],
        "modes_washes": [],

        # Beams
        "beams": "",
        "manufacturer_beams": "",
        "universe_beams": "",
        "address_beams": "",
        "watt_beams": "",
        "phase_beams": "",
        "models_beams": [],
        "modes_beams": [],

        # Blinder
        "blinders": "",
        "manufacturer_blinders": "",
        "universe_blinders": "",
        "address_blinders": "",
        "watt_blinders": "",
        "phase_blinders": "",
        "models_blinders": [],
        "modes_blinders": [],

        # Strobes
        "strobes": "",
        "manufacturer_strobes": "",
        "universe_strobes": "",
        "address_strobes": "",
        "watt_strobes": "",
        "phase_strobes": "",
        "models_strobes": [],
        "modes_strobes": [],

        # Positionen / Truss / Hinweise
        "positions": "",
        "notes": "",
        "count_spots": "",
        "count_washes": "",
        "count_beams": "",
        "count_blinders": "",
        "count_strobes": "",
        "truss_info": "",
        "truss_height": "",
        "specials": "",

        # Strom / Infrastruktur
        "power_main": "",
        "power_light": "",
        "power_sound": "",
        "power_video": "",
        "power_foh": "",
        "power_other": "",
    }


def _empty_checklists() -> Dict:
    return {
        "preproduction": [],
        "aufbau": [],
        "show": [],
    }


def load_data() -> None:
    """Lädt Shows + IDs aus shows.json, falls vorhanden, und sorgt für Defaults."""
    global shows, next_show_id, next_song_id, next_check_item_id

    if not os.path.exists(DATA_FILE):
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    shows_data = data.get("shows", [])
    next_show_id = data.get("next_show_id", 1)
    next_song_id = data.get("next_song_id", 1)
    next_check_item_id = data.get("next_check_item_id", 1)

    normalized_shows: List[Show] = []
    for raw_show in shows_data:
        show = dict(raw_show)

        # Basisfelder
        show.setdefault("id", len(normalized_shows) + 1)
        show.setdefault("name", f"Show {show.get('id', 0)}")
        show.setdefault("artist", "")
        show.setdefault("date", "")
        show.setdefault("venue_type", "")
        show.setdefault("genre", "")
        show.setdefault("rig_type", "")

        # Stammdaten-Extras
        for key in ("regie", "veranstalter", "vt_firma", "technischer_leiter", "notes"):
            show.setdefault(key, "")

        # Songs-Liste
        songs_list = show.get("songs")
        if not isinstance(songs_list, list):
            songs_list = []
        for idx, s in enumerate(songs_list, start=1):
            s.setdefault("id", idx)
            s.setdefault("order_index", idx)
            s.setdefault("name", f"Song {idx}")
            s.setdefault("mood", "")
            s.setdefault("colors", "")
            s.setdefault("movement_style", "")
            s.setdefault("eye_candy", "")
            s.setdefault("special_notes", "")
            s.setdefault("general_notes", "")
            s.setdefault("prop_images", [])
        show["songs"] = songs_list

        # Rig-Struktur
        rig = show.get("rig_setup")
        if not isinstance(rig, dict):
            rig = _empty_rig_setup()
        else:
            defaults = _empty_rig_setup()
            for key, default_val in defaults.items():
                rig.setdefault(key, default_val)
        show["rig_setup"] = rig

        # Checklisten-Struktur
        cl = show.get("checklists")
        if not isinstance(cl, dict):
            cl = _empty_checklists()
        else:
            for key in ("preproduction", "aufbau", "show"):
                items = cl.get(key)
                if not isinstance(items, list):
                    items = []
                cl[key] = items
        show["checklists"] = cl

        normalized_shows.append(show)

    # Wichtig: Liste nicht neu binden, sondern Inhalt ersetzen,
    # damit andere Module (routes_shows) dieselbe Liste sehen.
    shows.clear()
    shows.extend(normalized_shows)


def save_data() -> None:
    """Speichert Shows + IDs nach shows.json."""
    data = {
        "shows": shows,
        "next_show_id": next_show_id,
        "next_song_id": next_song_id,
        "next_check_item_id": next_check_item_id,
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_show(show_id: int) -> Optional[Show]:
    for show in shows:
        if show.get("id") == show_id:
            return show
    return None


def create_default_show(
    name: str,
    artist: str,
    date: str,
    venue_type: str,
    genre: str,
    rig_type: str,
) -> Show:
    """Neue Show mit Default-Struktur anlegen (nur in-memory + JSON)."""
    global next_show_id

    show: Show = {
        "id": next_show_id,
        "name": name or f"Show {next_show_id}",
        "artist": artist or "",
        "date": date or "",
        "venue_type": venue_type or "",
        "genre": genre or "",
        "rig_type": rig_type or "",
        "regie": "",
        "veranstalter": "",
        "vt_firma": "",
        "technischer_leiter": "",
        "notes": "",
        "songs": [],
        "rig_setup": _empty_rig_setup(),
        "checklists": _empty_checklists(),
    }

    next_show_id += 1
    return show


def create_song(
    show: Show,
    name: str,
    mood: str,
    colors: str,
    movement_style: str,
    eye_candy: str,
    special_notes: str,
    general_notes: str,
) -> Song:
    """Fügt der Show einen neuen Song/Szene hinzu."""
    global next_song_id

    order_index = len(show["songs"]) + 1

    song: Song = {
        "id": next_song_id,
        "name": name or f"Song {order_index}",
        "order_index": order_index,
        "mood": mood or "",
        "colors": colors or "",
        "movement_style": movement_style or "",
        "eye_candy": eye_candy or "",
        "special_notes": special_notes or "",
        "general_notes": general_notes or "",
    }

    next_song_id += 1
    show["songs"].append(song)
    return song


def remove_song_from_show(show: Show, song_id: int) -> None:
    """Entfernt einen Song aus der Show und nummeriert neu durch."""
    songs_list = show.get("songs", [])
    songs_list = [s for s in songs_list if s.get("id") != song_id]
    for idx, s in enumerate(songs_list, start=1):
        s["order_index"] = idx
    show["songs"] = songs_list


def create_check_item(show: Show, category: str, text: str) -> None:
    """Fügt einen neuen Punkt zur angegebenen Checkliste hinzu."""
    global next_check_item_id

    if "checklists" not in show or not isinstance(show["checklists"], dict):
        show["checklists"] = _empty_checklists()

    if category not in show["checklists"]:
        return

    item = {
        "id": next_check_item_id,
        "text": text,
        "done": False,
    }
    next_check_item_id += 1
    show["checklists"][category].append(item)


def toggle_check_item(show: Show, category: str, item_id: int) -> None:
    """Schaltet den Status eines Checklisten-Eintrags um."""
    if "checklists" not in show or category not in show["checklists"]:
        return

    for item in show["checklists"][category]:
        if item.get("id") == item_id:
            item["done"] = not item.get("done", False)
            break


def remove_show(show_id: int) -> None:
    """Entfernt eine komplette Show aus der Liste."""
    global shows
    shows = [s for s in shows if s.get("id") != show_id]


def duplicate_show(show_id: int) -> Optional[Show]:
    """Erzeugt eine Kopie einer bestehenden Show (inkl. Songs & Checklisten)."""
    global shows, next_show_id, next_song_id, next_check_item_id

    original = find_show(show_id)
    if not original:
        return None

    new_show: Show = copy.deepcopy(original)
    new_show["id"] = next_show_id
    next_show_id += 1

    base_name = new_show.get("name") or f"Show {new_show['id']}"
    new_show["name"] = f"{base_name} (Kopie)"
    new_show["date"] = ""  # Datum bei Kopie leeren

    # Songs: neue IDs + saubere order_index
    new_songs: List[Song] = []
    for idx, song in enumerate(new_show.get("songs", []), start=1):
        song["id"] = next_song_id
        song["order_index"] = idx
        next_song_id += 1
        new_songs.append(song)
    new_show["songs"] = new_songs

    # Checklisten: neue Item-IDs
    cl = new_show.get("checklists")
    if isinstance(cl, dict):
        for key in ("preproduction", "aufbau", "show"):
            items = cl.get(key, [])
            if not isinstance(items, list):
                cl[key] = []
                continue
            new_items = []
            for item in items:
                item["id"] = next_check_item_id
                next_check_item_id += 1
                new_items.append(item)
            cl[key] = new_items

    shows.append(new_show)
    save_data()

    # DB-Sync für die Kopie
    sync_entire_show_to_db(new_show)

    return new_show


# -----------------------------------------------------------------------------#
# DB-Sync: komplette Show in SQLite spiegeln
# -----------------------------------------------------------------------------#


def sync_entire_show_to_db(show: Show) -> None:
    """
    Spiegelt eine komplette Show (Stammdaten, Rig, Songs, Checklisten)
    in die SQLite-DB. JSON bleibt weiterhin die führende Quelle.
    """
    show_id = show.get("id")
    if show_id is None:
        return

    try:
        # Show-Objekt holen oder neu anlegen
        db_show = ShowModel.query.get(show_id)
        if not db_show:
            db_show = ShowModel(id=show_id)
            db.session.add(db_show)

        # Stammdaten
        db_show.name = show.get("name", "") or ""
        db_show.artist = show.get("artist", "") or ""
        db_show.date = show.get("date", "") or ""
        db_show.venue_type = show.get("venue_type", "") or ""
        db_show.genre = show.get("genre", "") or ""
        db_show.rig_type = show.get("rig_type", "") or ""
        db_show.regie = show.get("regie", "") or ""
        db_show.veranstalter = show.get("veranstalter", "") or ""
        db_show.vt_firma = show.get("vt_firma", "") or ""
        db_show.technischer_leiter = show.get("technischer_leiter", "") or ""
        db_show.notes = show.get("notes", "") or ""
        db_show.ma3_sequence_id = show.get("ma3_sequence_id", 101)


        # Rig / Strom
        rig = show.get("rig_setup") or {}
        if not isinstance(rig, dict):
            rig = {}

        db_show.rig_manufacturer = (
            rig.get("main_brand") or rig.get("manufacturer") or ""
        )

        db_show.rig_spots = rig.get("spots", "") or ""
        db_show.rig_washes = rig.get("washes", "") or ""
        db_show.rig_beams = rig.get("beams", "") or ""
        db_show.rig_blinders = rig.get("blinders", "") or ""
        db_show.rig_strobes = rig.get("strobes", "") or ""

        db_show.rig_positions = rig.get("positions", "") or ""
        db_show.rig_notes = rig.get("notes", "") or ""

        db_show.power_main = rig.get("power_main", "") or ""
        db_show.power_light = rig.get("power_light", "") or ""
        db_show.power_sound = rig.get("power_sound", "") or ""
        db_show.power_video = rig.get("power_video", "") or ""
        db_show.power_foh = rig.get("power_foh", "") or ""
        db_show.power_other = rig.get("power_other", "") or ""

        # Songs: vorhandene DB-Songs löschen und aus JSON neu aufbauen
        SongModel.query.filter_by(show_id=show_id).delete()
        songs_list = show.get("songs") or []
        if isinstance(songs_list, list):
            for s in songs_list:
                db_song = SongModel(
                    show_id=show_id,
                    order_index=s.get("order_index", 1) or 1,
                    name=s.get("name", "") or "",
                    mood=s.get("mood", "") or "",
                    colors=s.get("colors", "") or "",
                    movement_style=s.get("movement_style", "") or "",
                    eye_candy=s.get("eye_candy", "") or "",
                    special_notes=s.get("special_notes", "") or "",
                    general_notes=s.get("general_notes", "") or "",
                )
                db.session.add(db_song)

        # Checklisten: ebenfalls komplett neu schreiben
        ChecklistItemModel.query.filter_by(show_id=show_id).delete()
        cl = show.get("checklists") or {}
        if isinstance(cl, dict):
            for category in ("preproduction", "aufbau", "show"):
                items = cl.get(category) or []
                if not isinstance(items, list):
                    continue
                for item in items:
                    text = item.get("text", "") or ""
                    done = bool(item.get("done", False))
                    db_ci = ChecklistItemModel(
                        show_id=show_id,
                        category=category,
                        text=text,
                        done=done,
                    )
                    db.session.add(db_ci)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[DB-SYNC] Fehler beim Synchronisieren der Show {show_id}: {e}")


# Beim Import einmal Daten laden
load_data()