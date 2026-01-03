from flask import request, redirect, url_for, abort
from app import app
from models import db, ContactPersonModel
from show_logic import find_show, sync_entire_show_to_db, save_data


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

    # Ensure JSON + DB stay in sync if needed
    try:
        save_data()
        sync_entire_show_to_db(show)
    except Exception:
        pass

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
