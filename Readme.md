# Lichtdesign-Assistent v2

A small web application for lighting designers and operators to plan shows, document rigs and scenes, and export clean PDFs (Show Report & Tech Rider).

The focus is on **clear communication** between lighting, production, and venue:
- Capture show master data
- Document rig / setup
- Describe songs / scenes in detail
- Track checklists and notes
- Export everything as **PDF**

---

## 1. Use Case & Audience

- Lighting designers / operators (touring or local)
- Small to mid-sized productions, clubs, festivals, corporate events
- Situations where you need structured information for:
  - What the lighting needs
  - How the rig looks (counts, positions, notes)
  - Which scenes / moods are planned
  - What the venue / provider has to prepare

---

## 2. Features

### 2.1 Show Dashboard

- Create new shows with:
  - Show / project name  
  - Artist / production  
  - Date (with date picker)  
  - Venue type (club, hall, open air, …)  
  - Genre / style  
  - Rig type (touring, house rig, …)
- Shows are listed on the right with:
  - Name, artist, date, venue, rig type, scene count
- Actions per show:
  - **Open** – go to the detailed view
  - **Duplicate** – copy a show (useful for tour dates)
  - **Delete Show** – remove a show (with confirmation)

---

### 2.2 Show Detail View

Each show has its own detail page with several sections.

#### 2.2.1 Master Data

- Editable at any time:
  - Show name
  - Artist / production
  - Date
  - Venue type
  - Genre / style
  - Rig type
  - Promoter
  - Production company
  - Technical director
- Changes are saved via a simple “Save” button.

#### 2.2.2 Rig / Setup

- Fixture counts:
  - Spots, Washes, Beams, Blinders, Strobes
- Text fields for:
  - Positions (front, side, back, floor, etc.)
  - Special notes (truss, height, power, special requirements)
- Stored with a dedicated **Save Rig** button.

#### 2.2.3 Songs / Scenes

- List of scenes with:
  - Scene number + name
  - Mood
  - Colours
  - Movement
  - Eye-candy
  - Specials
  - Notes
- Scenes can be:
  - Added
  - Edited inline
  - Deleted individually
- Scene numbers remain clear and ordered.

#### 2.2.4 Checklist

- Items consist of:
  - Checkbox (done / open)
  - Title
  - Note (e.g. “Request power plan from venue”)
- Inline editing for all fields.
- Saving does **not** cause annoying scroll jumps – the page stays where you are.

---

## 3. PDF Export

Two different PDFs are generated server-side using **ReportLab**.

### 3.1 Show Report

- Logo at the top left (LightBlast logo)
- Title: `Lichtdesign-Assistent – Show Report`
- Content:
  - Show master data (name, artist, date, venue type, genre, rig type)
  - List of all songs / scenes with:
    - Number + name
    - Mood
    - Colours
    - Movement
    - Eye-candy
    - Specials
    - Notes

### 3.2 Tech Rider

- Logo at the top left
- Title: `Lichtdesign-Assistent – Tech Rider`
- Content focuses on:
  - Show master data
  - Rig / setup (counts, positions)
  - Special notes (truss, height, power, limitations, etc.)
  - Relevant checklist items for venue / provider / rental company

File names are based on the show name, for example:

- `Light_Blast_Show_Report.pdf`
- `Light_Blast_Tech_Rider.pdf`

Spaces and special characters are cleaned when generating the filename.

---

## 4. Tech Stack

- **Backend:** Python 3 + Flask  
- **Templating:** Jinja2  
- **Frontend:** Bootstrap 5 (CDN) + custom CSS in `layout.html`  
- **PDF Generation:** ReportLab  
- **Static Files:** `/static/staticimg` (logos, images)

---

## 5. Project Structure (simplified)

```text
lichtdesign-assistent-v2/
│
├─ app.py                  # Main Flask application (routes, logic, PDF export)
│
├─ App/
│   ├─ index.html          # Dashboard: create shows, list, duplicate, delete
│   ├─ layout.html         # Base layout, navbar, logo, styles
│   └─ show_detail.html    # Show detail view (master data, rig, scenes, checklist)
│
├─ static/
│   └─ staticimg/
│       ├─ LightBlastblack.png   # Main logo for navbar & PDFs
│       └─ staticimglogo.png     # Additional / fallback logo
│
└─ README.md               # This file


Webbasierter Assistent für Lichtdesigner:innen zur strukturierten Show-Planung, Szenenverwaltung und PDF-Exports (Show-Report & Tech-Rider).

Der Fokus liegt auf **klarer Kommunikation** zwischen Licht, Produktion und Veranstalter:
- Show-Stammdaten sauber erfassen
- Rig / Setup dokumentieren
- Songs / Szenen mit Lichtstimmungen beschreiben
- Checklisten und Notizen festhalten
- Alles als **PDF** exportieren (Show-Report & Tech-Rider)

---

## 1. Zielgruppe & Use Case

- Lichtdesigner:innen, Operator:innen, Touring-LDs  
- kleine bis mittlere Produktionen, Clubs, Festivals, Firmenveranstaltungen  
- Vorbereitung von Shows, bei denen **Abstimmung und Dokumentation** wichtig sind:
  - Was braucht das Licht?
  - Wie sieht das Rig aus?
  - Welche Stimmungen / Szenen sind geplant?
  - Was muss Technik / Venue wissen (Strom, Truss, Besonderheiten …)?

---

## 2. Funktionsübersicht (Stand v2)

### 2.1 Show-Übersicht (Dashboard)

- Neue Shows anlegen mit:
  - Show- / Projektname
  - Artist / Produktion
  - Datum (inkl. Date-Picker)
  - Venue-Typ (z.B. Club, Halle, Open Air …)
  - Genre / Stil
  - Rig-Typ (z.B. Touring, Hausrig …)
- Liste aller Shows rechts:
  - Anzeige von Name, Artist, Datum, Venue, Rig-Typ
  - Buttons:
    - **Öffnen** – Details, Szenen & Checkliste bearbeiten
    - **Duplizieren** – Show kopieren (z.B. für zweiten Tourtermin)
    - **Show löschen** – Show komplett entfernen (mit Sicherheitsabfrage)

### 2.2 Show-Detailseite

Für jede Show gibt es eine Detailseite mit mehreren Bereichen:

1. **Show-Stammdaten**
   - Bearbeitbar: Name, Artist, Datum, Venue, Genre, Rig-Typ, Veranstalter, VT-Firma, Technischer Leiter usw.
   - Änderungen können jederzeit gespeichert werden.

2. **Rig / Setup**
   - Anzahl: Spots, Washes, Beams, Blinder, Strobes
   - Textfeld für Positionen (z.B. Front, Side, Back, Floor …)
   - Textfeld für besondere Hinweise / Truss / Höhe / Besonderheiten
   - Speichern-Button zum Aktualisieren der Rig-Infos

3. **Songs / Szenen**
   - Szenenliste mit:
     - Nummer + Name
     - Stimmung
     - Farben
     - Bewegung
     - Eye-Candy
     - Specials
     - Notizen
   - Szenen können:
     - hinzugefügt
     - einzeln bearbeitet
     - einzeln gelöscht
   - Reihenfolge und Nummerierung bleiben klar erkennbar.

4. **Checkliste**
   - Punkte mit:
     - Checkbox (erledigt / offen)
     - Titel
     - Notizfeld (z.B. „Stromplan vom Venue anfordern“)
   - Einträge sind direkt inline editierbar.
   - Beim Speichern bleibt die Scrollposition stabil (kein nerviges Hin- und Herspringen).

### 2.3 PDF-Export

Aktuell gibt es zwei getrennte PDFs:

1. **Show-Report (Show-Report-PDF)**
   - Logo oben links (LightBlast-Logo)
   - Titel: „Lichtdesign-Assistent – Show Report“
   - Show-Stammdaten:
     - Showname
     - Artist / Produktion
     - Datum
     - Venue-Typ
     - Genre
     - Rig-Typ
   - Liste aller Songs / Szenen mit:
     - Nummer + Name
     - Stimmung
     - Farben
     - Bewegung
     - Eye-Candy
     - Specials
     - Notizen

2. **Tech-Rider (Tech-Rider-PDF)**
   - Logo oben links
   - Titel: „Lichtdesign-Assistent – Tech Rider“
   - Fokus auf:
     - Show-Stammdaten
     - Rig / Setup (Anzahlen, Positionen)
     - Besondere Hinweise / Truss / Höhe / Strom / Besonderheiten
     - Checklisten-Punkte, die für Venue / Technik relevant sind

Beide PDFs werden serverseitig mit **ReportLab** erzeugt und als Download bereitgestellt.  
Der Dateiname orientiert sich am Shownamen, z.B.:

- `Light_Blast_Show_Report.pdf`
- `Light_Blast_Tech_Rider.pdf`

(Leerzeichen, Sonderzeichen etc. werden beim Export bereinigt.)

---

## 3. Technischer Stack

- **Backend:** Python 3.x + Flask
- **Templating:** Jinja2
- **Frontend:** Bootstrap 5 (CDN), Custom CSS in `layout.html`
- **PDF:** ReportLab
- **Assets:** statische Dateien (Logo) unter `static/staticimg`

---

## 4. Projektstruktur (vereinfacht)

```text
lichtdesign-assistent-v2/
│
├─ app.py                  # Zentrale Flask-App (Routen, Logik, PDF-Export)
│
├─ App/
│   ├─ index.html          # Dashboard: Shows anlegen, Liste, Duplizieren, Löschen
│   ├─ layout.html         # Grundlayout, Navigation, Logo, Styles
│   └─ show_detail.html    # Detailansicht einer Show (Stammdaten, Rig, Szenen, Checkliste)
│
├─ static/
│   └─ staticimg/
│       ├─ LightBlastblack.png   # Logo für Navbar & PDFs
│       └─ staticimglogo.png     # ggf. anderes Logo / Fallback
│
└─ README.md               # Dieses Dokument
