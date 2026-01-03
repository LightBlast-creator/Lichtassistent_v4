from flask_sqlalchemy import SQLAlchemy

# Zentrales DB-Objekt für die ganze App
db = SQLAlchemy()


class Show(db.Model):
    __tablename__ = "shows"

    id = db.Column(db.Integer, primary_key=True)

    # Stammdaten
    name = db.Column(db.String(200), nullable=False, default="")
    artist = db.Column(db.String(200), default="")
    date = db.Column(db.String(20), default="")  # wir lassen das Datum als String
    venue_type = db.Column(db.String(100), default="")
    genre = db.Column(db.String(100), default="")
    rig_type = db.Column(db.String(100), default="")

    regie = db.Column(db.String(200), default="")
    veranstalter = db.Column(db.String(200), default="")
    vt_firma = db.Column(db.String(200), default="")
    technischer_leiter = db.Column(db.String(200), default="")
    notes = db.Column(db.Text, default="")

    # MA3-spezifisch
    # Standard-Sequence-ID für den Export (z.B. 101, 201, 301 ...)
    ma3_sequence_id = db.Column(db.Integer, nullable=False, default=101)

    # Rig-Infos (vereinfacht direkt an der Show)
    rig_manufacturer = db.Column(db.String(200), default="")

    rig_spots = db.Column(db.String(200), default="")
    rig_washes = db.Column(db.String(200), default="")
    rig_beams = db.Column(db.String(200), default="")
    rig_blinders = db.Column(db.String(200), default="")
    rig_strobes = db.Column(db.String(200), default="")

    rig_positions = db.Column(db.Text, default="")
    rig_notes = db.Column(db.Text, default="")

    power_main = db.Column(db.String(200), default="")
    power_light = db.Column(db.String(200), default="")
    power_sound = db.Column(db.String(200), default="")
    power_video = db.Column(db.String(200), default="")
    power_foh = db.Column(db.String(200), default="")
    power_other = db.Column(db.String(200), default="")

    # Beziehungen
    songs = db.relationship(
        "Song",
        backref="show",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Song.order_index",
    )
    checklist_items = db.relationship(
        "ChecklistItem",
        backref="show",
        lazy=True,
        cascade="all, delete-orphan",
    )
    contacts = db.relationship(
    "ContactPersonModel",
    backref="show",
    cascade="all, delete-orphan",
    order_by="ContactPersonModel.sort_order.asc()"
)



class Song(db.Model):
    __tablename__ = "songs"

    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey("shows.id"), nullable=False)

    order_index = db.Column(db.Integer, nullable=False, default=1)

    name = db.Column(db.String(200), nullable=False, default="")
    mood = db.Column(db.String(200), default="")
    colors = db.Column(db.String(200), default="")
    movement_style = db.Column(db.String(200), default="")
    eye_candy = db.Column(db.Text, default="")
    special_notes = db.Column(db.Text, default="")
    general_notes = db.Column(db.Text, default="")


class ChecklistItem(db.Model):
    __tablename__ = "checklist_items"

    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey("shows.id"), nullable=False)

    # "preproduction", "aufbau", "show"
    category = db.Column(db.String(50), nullable=False)

    text = db.Column(db.Text, nullable=False)
    done = db.Column(db.Boolean, nullable=False, default=False)

from datetime import datetime

class ContactPersonModel(db.Model):
    __tablename__ = "contact_persons"

    id = db.Column(db.Integer, primary_key=True)

    show_id = db.Column(db.Integer, db.ForeignKey("shows.id"), nullable=False, index=True)

    role = db.Column(db.String(80), nullable=False)        # z.B. Produktion, Projektleitung, Tech
    name = db.Column(db.String(120), nullable=True)
    company = db.Column(db.String(120), nullable=True)

    phone = db.Column(db.String(60), nullable=True)
    email = db.Column(db.String(160), nullable=True)

    notes = db.Column(db.Text, nullable=True)

    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
