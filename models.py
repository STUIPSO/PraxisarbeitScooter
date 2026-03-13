import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Datenbank-Instanz
db = SQLAlchemy()

# 1. Das User-Modell (Anforderung: Login, Email, Username, API-Zugriff)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    # API Token fuer Zugriff ohne Browser
    api_token = db.Column(db.String(100), unique=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        # Token automatisch generieren
        if not self.api_token:
            self.api_token = secrets.token_hex(16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. Die Geschaeftslogik: E-Scooter
class Scooter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bezeichnung = db.Column(db.String(100), nullable=False)
    batterie_status = db.Column(db.Integer, default=100) # In Prozent
    standort = db.Column(db.String(100), default="Zentrale")
    ist_verliehen = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        """Hilfsfunktion fuer die JSON-API"""
        return {
            'id': self.id,
            'name': self.bezeichnung,
            'batterie': self.batterie_status,
            'ort': self.standort,
            'status': 'verliehen' if self.ist_verliehen else 'frei'
        }
