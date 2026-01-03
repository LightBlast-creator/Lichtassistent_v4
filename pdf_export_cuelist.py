from typing import Dict, Tuple
import io
from reportlab.lib.pagesizes import A4  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore

Show = Dict

def build_cuelist_pdf(show: Show) -> Tuple[io.BytesIO, str]:
    """
    Erzeugt eine PDF nur mit der Cue-Liste (inkl. Marker für Lichttechnik).
    Gibt (BytesIO, Dateiname) zurück.
    """
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 50, f"Cue-Liste – {show.get('name', '')}")
    y = height - 90
    line_height = 18

    songs = show.get("songs") or []
    if songs:
        for song in songs:
            if y < 80:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica-Bold", 16)
                pdf.drawString(40, y, f"Cue-Liste – {show.get('name', '')}")
                y -= line_height
                pdf.setFont("Helvetica", 11)
            # Marker für Lichtler (z.B. farbiger Kreis)
            pdf.setFillColorRGB(0.2, 0.6, 1.0)  # Blau für Licht
            pdf.circle(50, y + 6, 5, fill=1)
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(65, y, f"{song.get('order_index', '')} – {song.get('name', '')}")
            y -= line_height
            pdf.setFont("Helvetica", 10)
            if song.get("mood"):
                pdf.drawString(80, y, f"Stimmung: {song.get('mood', '')}")
                y -= line_height
            if song.get("special_notes"):
                pdf.drawString(80, y, f"Regie: {song.get('special_notes', '')}")
                y -= line_height
            if song.get("general_notes"):
                pdf.drawString(80, y, f"Notiz: {song.get('general_notes', '')}")
                y -= line_height
            y -= 4
    else:
        pdf.drawString(50, y, "Keine Cues/Szenen erfasst.")
        y -= line_height

    pdf.save()
    buffer.seek(0)
    filename = f"Cue-Liste_{show.get('name','show')}.pdf"
    return buffer, filename
