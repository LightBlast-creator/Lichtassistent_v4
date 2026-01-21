import csv
from show_logic import find_show

def export_cues_to_csv(show_id: int, file_path: str):
    show = find_show(show_id)
    if not show:
        raise ValueError("Show not found")
    songs = show.get("songs", [])
    with open(file_path, "w", newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Cue Number", "Cue Name", "Notes"])  # ETC Nomad Standard
        for idx, song in enumerate(songs, 1):
            name = song.get("name", f"Cue {idx}")
            notes = song.get("notes", "")
            # Nur exportieren, wenn Name oder Notizen vorhanden sind
            if name.strip() or notes.strip():
                writer.writerow([
                    idx,
                    name,
                    notes
                ])
