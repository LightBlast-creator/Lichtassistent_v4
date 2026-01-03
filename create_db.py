# create_db.py
from app import app
from models import db

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Datenbanktabellen wurden erstellt.")
