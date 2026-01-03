from typing import Dict, Optional, Tuple
import os
import io

from reportlab.lib.pagesizes import A4  # type: ignore
from reportlab.lib.utils import ImageReader  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore

Show = Dict


def _find_logo_path() -> Optional[str]:
    """
    Sucht nach einem geeigneten Logo im static/staticimg-Verzeichnis.
    Gibt den absoluten Pfad zurück oder None, falls kein Logo gefunden wird.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    staticimg_dir = os.path.join(base_dir, "static", "staticimg")

    candidates = [
        os.path.join(staticimg_dir, "LightBlastblack .png"),
        os.path.join(staticimg_dir, "LightBlastblack.png"),
        os.path.join(staticimg_dir, "LightBlast_Logo_B_1024.png"),
        os.path.join(staticimg_dir, "staticimglogo.png"),
    ]

    for path in candidates:
        print("[LOGO-CHECK] Prüfe", path, "->", os.path.exists(path))
        if os.path.exists(path):
            return path

    if os.path.isdir(staticimg_dir):
        for fname in os.listdir(staticimg_dir):
            if fname.lower().endswith(".png"):
                fallback = os.path.join(staticimg_dir, fname)
                print("[LOGO-CHECK] Fallback PNG:", fallback)
                return fallback

    print("[LOGO-CHECK] Kein Logo gefunden")
    return None


def build_show_report_pdf(show: Show) -> Tuple[io.BytesIO, str]:
    """
    Erzeugt die interne Show-Report-PDF (Songs, Rig, Checklisten).
    Gibt (BytesIO, Dateiname) zurück.
    """
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Logo
    logo_path = _find_logo_path()
    if logo_path:
        try:
            logo = ImageReader(logo_path)
            orig_w, orig_h = logo.getSize()

            desired_width = 110.0
            scale = desired_width / float(orig_w)
            desired_height = orig_h * scale

            top_margin = 40.0
            x = 40.0
            y_logo = height - top_margin - desired_height

            pdf.drawImage(
                logo,
                x,
                y_logo,
                width=desired_width,
                height=desired_height,
                mask="auto",
                preserveAspectRatio=True,
            )
        except Exception as e:  # nur Logging
            print("[LOGO-CHECK] Fehler beim Laden des Logos:", e)

    # Kopf
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(180, height - 60, "Lichtdesign-Assistent – Show Report")

    pdf.setFont("Helvetica", 12)
    y = height - 140
    line_height = 18

    def write(label: str, value: str) -> None:
        nonlocal y
        pdf.drawString(40, y, f"{label}: {value if value else '–'}")
        y -= line_height

    write("Showname", show.get("name", ""))
    write("Artist / Produktion", show.get("artist", ""))
    write("Datum", show.get("date", ""))
    write("Venue-Typ", show.get("venue_type", ""))
    write("Genre", show.get("genre", ""))
    write("Rig-Typ", show.get("rig_type", ""))

    pdf.line(40, y, width - 40, y)
    y -= line_height

    # ---------------------------------------------------------------------#
    # Songs / Szenen (DETAIL)
    # ---------------------------------------------------------------------#
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Songs / Szenen")
    y -= line_height

    pdf.setFont("Helvetica", 11)

    songs = show.get("songs") or []
    if songs:
        for song in songs:
            if y < 100:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica-Bold", 14)
                pdf.drawString(40, y, "Songs / Szenen (Fortsetzung)")
                y -= line_height
                pdf.setFont("Helvetica", 11)

            title = f"{song.get('order_index', ''):>2} – {song.get('name', '')}"
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(50, y, title)
            y -= line_height

            pdf.setFont("Helvetica", 10)

            def write_song_line(label: str, key: str) -> None:
                nonlocal y
                text = song.get(key, "")
                if text:
                    pdf.drawString(60, y, f"{label}: {text}")
                    y -= line_height

            write_song_line("Stimmung", "mood")
            write_song_line("Farben", "colors")
            write_song_line("Bewegung", "movement_style")
            write_song_line("Eye-Candy", "eye_candy")
            write_song_line("Specials", "special_notes")
            write_song_line("Notizen", "general_notes")

            y -= line_height / 2
    else:
        pdf.drawString(50, y, "Keine Songs/Szenen erfasst.")
        y -= line_height

    # ---------------------------------------------------------------------#
    # Rig / Setup inkl. Strom
    # ---------------------------------------------------------------------#
    rig = show.get("rig_setup", {})
    if isinstance(rig, dict):
        rig_has_content = any(
            (rig.get(k) or "").strip()
            for k in [
                "main_brand",
                "manufacturer",
                "spots",
                "washes",
                "beams",
                "blinders",
                "strobes",
                "positions",
                "notes",
                "power_main",
                "power_light",
                "power_sound",
                "power_video",
                "power_foh",
                "power_other",
            ]
        )
        if rig_has_content:
            if y < 120:
                pdf.showPage()
                y = height - 60

            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(40, y, "Rig / Setup")
            y -= line_height
            pdf.setFont("Helvetica", 10)

            def write_rig_line(label: str, key: str) -> None:
                nonlocal y
                val = (rig.get(key) or "").strip()
                if not val:
                    return
                pdf.drawString(50, y, f"{label}: {val}")
                y -= line_height

            write_rig_line("Bevorzugter Hersteller", "main_brand")

            # Fixture-Übersicht
            write_rig_line("Spots (Anzahl)", "spots")
            write_rig_line("Washes (Anzahl)", "washes")
            write_rig_line("Beams (Anzahl)", "beams")
            write_rig_line("Blinder (Anzahl)", "blinders")
            write_rig_line("Strobes (Anzahl)", "strobes")

            positions = (rig.get("positions") or "").strip()
            if positions:
                pdf.drawString(50, y, f"Positionen: {positions}")
                y -= line_height

            notes_rig = (rig.get("notes") or "").strip()
            if notes_rig:
                pdf.drawString(50, y, f"Besondere Hinweise / Truss / Höhe: {notes_rig}")
                y -= line_height

            # Strom / Infrastruktur
            power_main = (rig.get("power_main") or "").strip()
            power_light = (rig.get("power_light") or "").strip()
            power_sound = (rig.get("power_sound") or "").strip()
            power_video = (rig.get("power_video") or "").strip()
            power_foh = (rig.get("power_foh") or "").strip()
            power_other = (rig.get("power_other") or "").strip()

            if any([power_main, power_light, power_sound, power_video, power_foh, power_other]):
                y -= line_height * 0.5
                if y < 80:
                    pdf.showPage()
                    y = height - 60
                    pdf.setFont("Helvetica-Bold", 14)
                    pdf.drawString(40, y, "Rig / Setup (Fortsetzung)")
                    y -= line_height
                    pdf.setFont("Helvetica", 10)

                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(50, y, "Strom / Infrastruktur")
                y -= line_height
                pdf.setFont("Helvetica", 10)

                if power_main:
                    pdf.drawString(60, y, f"Hauptversorgung: {power_main}")
                    y -= line_height
                if power_light:
                    pdf.drawString(60, y, f"Licht / Dimmer: {power_light}")
                    y -= line_height
                if power_sound:
                    pdf.drawString(60, y, f"Audio: {power_sound}")
                    y -= line_height
                if power_video:
                    pdf.drawString(60, y, f"Video / LED: {power_video}")
                    y -= line_height
                if power_foh:
                    pdf.drawString(60, y, f"FOH / Pultplatz: {power_foh}")
                    y -= line_height
                if power_other:
                    pdf.drawString(60, y, f"Sonstiges: {power_other}")
                    y -= line_height

            y -= line_height / 2

    # ---------------------------------------------------------------------#
    # Checklisten (DETAIL)
    # ---------------------------------------------------------------------#
    checklists = show.get("checklists", {})
    if isinstance(checklists, dict):
        if y < 120:
            pdf.showPage()
            y = height - 60

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, y, "Checklisten")
        y -= line_height

        def ensure_space_for_block(min_height: float, heading: str) -> None:
            nonlocal y
            if y < min_height:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica-Bold", 14)
                pdf.drawString(40, y, f"{heading} (Fortsetzung)")
                y -= line_height
                pdf.setFont("Helvetica", 10)

        sections = [
            ("preproduction", "Preproduction"),
            ("aufbau", "Aufbau"),
            ("show", "Showtag"),
        ]

        pdf.setFont("Helvetica", 10)

        for key, label in sections:
            items = checklists.get(key, [])
            if not isinstance(items, list) or not items:
                continue

            ensure_space_for_block(80, "Checklisten")

            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(50, y, label)
            y -= line_height

            pdf.setFont("Helvetica", 10)
            for item in items:
                if y < 60:
                    pdf.showPage()
                    y = height - 60
                    pdf.setFont("Helvetica-Bold", 14)
                    pdf.drawString(40, y, "Checklisten (Fortsetzung)")
                    y -= line_height
                    pdf.setFont("Helvetica-Bold", 11)
                    pdf.drawString(50, y, label)
                    y -= line_height
                    pdf.setFont("Helvetica", 10)

                text = item.get("text", "")
                done = bool(item.get("done", False))
                prefix = "[x]" if done else "[ ]"
                pdf.drawString(60, y, f"{prefix} {text}")
                y -= line_height * 0.9

            y -= line_height * 0.5

    # -------------------------------------------------------------
    # Requisiten-Bilder (prop_images)
    # -------------------------------------------------------------
    prop_images = show.get("prop_images", [])
    if prop_images:
        if y < 180:
            pdf.showPage()
            y = height - 60
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, y, "Requisiten-Bilder")
        y -= line_height
        thumb_size = 90
        margin = 20
        x = 40
        for idx, img_name in enumerate(prop_images):
            img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "props", img_name)
            try:
                img = ImageReader(img_path)
                pdf.drawImage(img, x, y - thumb_size, width=thumb_size, height=thumb_size, preserveAspectRatio=True, mask='auto')
                x += thumb_size + margin
                if x + thumb_size > width - 40:
                    x = 40
                    y -= thumb_size + margin
            except Exception as e:
                pdf.setFont("Helvetica-Oblique", 8)
                pdf.drawString(x, y, f"[Fehler beim Laden: {img_name}]")
                x += thumb_size + margin
                if x + thumb_size > width - 40:
                    x = 40
                    y -= thumb_size + margin

        y -= thumb_size + margin

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(40, 40, "Automatisch generiert mit dem Lichtdesign-Assistent v2")

    pdf.save()
    buffer.seek(0)

    filename = (show.get("name") or "show").replace(" ", "_") + ".pdf"
    return buffer, filename


def build_techrider_pdf(show: Show) -> Tuple[io.BytesIO, str]:
    """
    Erzeugt die externe Tech-Rider-PDF.
    Gibt (BytesIO, Dateiname) zurück.
    """
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Logo
    logo_path = _find_logo_path()
    if logo_path:
        try:
            logo = ImageReader(logo_path)
            orig_w, orig_h = logo.getSize()

            desired_width = 110.0
            scale = desired_width / float(orig_w)
            desired_height = orig_h * scale

            top_margin = 40.0
            x = 40.0
            y_logo = height - top_margin - desired_height

            pdf.drawImage(
                logo,
                x,
                y_logo,
                width=desired_width,
                height=desired_height,
                mask="auto",
                preserveAspectRatio=True,
            )
        except Exception as e:  # nur Logging
            print("[LOGO-CHECK] Fehler beim Laden des Logos:", e)

    # Kopf
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(180, height - 60, "Lichtdesign-Assistent – Tech Rider")

    pdf.setFont("Helvetica", 12)
    y = height - 140
    line_height = 18

    def write(label: str, value: str) -> None:
        nonlocal y
        pdf.drawString(40, y, f"{label}: {value if value else '–'}")
        y -= line_height

    # Stammdaten
    write("Showname", show.get("name", ""))
    write("Artist / Produktion", show.get("artist", ""))
    write("Datum", show.get("date", ""))
    write("Venue-Typ", show.get("venue_type", ""))
    write("Genre", show.get("genre", ""))
    write("Rig-Typ", show.get("rig_type", ""))

    pdf.line(40, y, width - 40, y)
    y -= line_height

    # Kontaktdaten / Verantwortliche
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Kontaktdaten / Verantwortliche")
    y -= line_height

    pdf.setFont("Helvetica", 11)
    write("Regie", show.get("regie", ""))
    write("Veranstalter", show.get("veranstalter", ""))
    write("VT-Firma", show.get("vt_firma", ""))
    write("Technischer Leiter", show.get("technischer_leiter", ""))

    # Allgemeine Notizen / Hinweise
    notes = (show.get("notes") or "").strip()
    if notes:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "Allgemeine Hinweise / Notizen")
        y -= line_height
        pdf.setFont("Helvetica", 10)

        max_chars = 90
        while notes:
            line = notes[:max_chars]
            notes = notes[max_chars:]
            if y < 60:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica", 10)
            pdf.drawString(50, y, line)
            y -= line_height * 0.9

        y -= line_height * 0.5

    # ---------------------------------------------------------------------#
    # Setlist (Übersicht)
    # ---------------------------------------------------------------------#
    songs = show.get("songs", []) or []
    if isinstance(songs, list) and songs:
        if y < 140:
            pdf.showPage()
            y = height - 60

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, y, "Setlist (Übersicht)")
        y -= line_height

        pdf.setFont("Helvetica", 10)
        for song in sorted(songs, key=lambda s: s.get("order_index", 0)):
            if y < 60:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica-Bold", 14)
                pdf.drawString(40, y, "Setlist (Fortsetzung)")
                y -= line_height
                pdf.setFont("Helvetica", 10)

            name = song.get("name", "")
            idx = song.get("order_index", "")
            mood = (song.get("mood") or "").strip()
            line = f"{idx:02d} – {name}"
            if mood:
                line += f"  (Stimmung: {mood})"

            pdf.drawString(50, y, line)
            y -= line_height * 0.9

        y -= line_height * 0.5

    # ---------------------------------------------------------------------#
    # Rig / Setup inkl. Strom – Anforderungen
    # ---------------------------------------------------------------------#
    rig = show.get("rig_setup", {})
    if isinstance(rig, dict):
        rig_has_content = any(
            (rig.get(k) or "").strip()
            for k in [
                "main_brand",
                "manufacturer",
                "spots",
                "washes",
                "beams",
                "blinders",
                "strobes",
                "positions",
                "notes",
                "power_main",
                "power_light",
                "power_sound",
                "power_video",
                "power_foh",
                "power_other",
            ]
        )
        if rig_has_content:
            if y < 140:
                pdf.showPage()
                y = height - 60

            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(40, y, "Rig / Setup – Anforderungen")
            y -= line_height
            pdf.setFont("Helvetica", 10)

            def write_rig_line(label: str, key: str) -> None:
                nonlocal y
                val = (rig.get(key) or "").strip()
                if not val:
                    return
                if y < 60:
                    pdf.showPage()
                    y = height - 60
                    pdf.setFont("Helvetica", 10)
                pdf.drawString(50, y, f"{label}: {val}")
                y -= line_height

            write_rig_line("Bevorzugter Hersteller", "main_brand")

            # Fixtures grob
            write_rig_line("Spots (Anzahl)", "spots")
            write_rig_line("Washes (Anzahl)", "washes")
            write_rig_line("Beams (Anzahl)", "beams")
            write_rig_line("Blinder (Anzahl)", "blinders")
            write_rig_line("Strobes (Anzahl)", "strobes")

            positions = (rig.get("positions") or "").strip()
            if positions:
                if y < 60:
                    pdf.showPage()
                    y = height - 60
                    pdf.setFont("Helvetica", 10)
                pdf.drawString(50, y, f"Positionen (Front/Side/Back/Floor): {positions}")
                y -= line_height

            notes_rig = (rig.get("notes") or "").strip()
            if notes_rig:
                if y < 60:
                    pdf.showPage()
                    y = height - 60
                    pdf.setFont("Helvetica", 10)
                pdf.drawString(50, y, f"Besondere Hinweise / Truss / Höhe: {notes_rig}")
                y -= line_height

            # Strom / Infrastruktur – zentraler Teil des Tech-Riders
            power_main = (rig.get("power_main") or "").strip()
            power_light = (rig.get("power_light") or "").strip()
            power_sound = (rig.get("power_sound") or "").strip()
            power_video = (rig.get("power_video") or "").strip()
            power_foh = (rig.get("power_foh") or "").strip()
            power_other = (rig.get("power_other") or "").strip()

            if any([power_main, power_light, power_sound, power_video, power_foh, power_other]):
                y -= line_height * 0.5
                if y < 80:
                    pdf.showPage()
                    y = height - 60
                    pdf.setFont("Helvetica", 10)

                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(50, y, "Strom / Infrastruktur (Anforderungen)")
                y -= line_height
                pdf.setFont("Helvetica", 10)

                if power_main:
                    pdf.drawString(60, y, f"Hauptversorgung: {power_main}")
                    y -= line_height
                if power_light:
                    pdf.drawString(60, y, f"Licht / Dimmer: {power_light}")
                    y -= line_height
                if power_sound:
                    pdf.drawString(60, y, f"Audio: {power_sound}")
                    y -= line_height
                if power_video:
                    pdf.drawString(60, y, f"Video / LED: {power_video}")
                    y -= line_height
                if power_foh:
                    pdf.drawString(60, y, f"FOH / Pultplatz: {power_foh}")
                    y -= line_height
                if power_other:
                    pdf.drawString(60, y, f"Sonstiges: {power_other}")
                    y -= line_height

            y -= line_height * 0.5

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        40,
        40,
        "Detail-Checklisten und Szenen-Infos siehe Show-Report (internes Dokument).",
    )

    pdf.save()
    buffer.seek(0)

    filename_base = (show.get("name") or "show").replace(" ", "_")
    filename = filename_base + "_TechRider.pdf"
    return buffer, filename
