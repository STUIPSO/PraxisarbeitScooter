# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Scooter
from functools import wraps
import qrcode
from io import BytesIO

app = Flask(__name__)

# --- KONFIGURATION ---
app.config['SECRET_KEY'] = '8230b31b845259d16afbd0b0ba6de09f70b0d6113f8a18dd1eab2bb72e12cbfd'
# WICHTIG: Ersetzen Sie 'geheim' durch Ihr Datenbank-Passwort!
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flaskuser:Password123$@localhost/praxisarbeit_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HILFSFUNKTION: API SCHUTZ ---
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-API-KEY')
        if not token:
            return jsonify({'error': 'Kein API Token. Zugriff verweigert.'}), 401
        user = User.query.filter_by(api_token=token).first()
        if not user:
            return jsonify({'error': 'Ungueltiger Token.'}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTEN (BROWSER) ---

@app.route('/')
def index():
    scooters = Scooter.query.all()
    return render_template('index.html', scooters=scooters)

@app.route('/qrcode/<int:scooter_id>')
def generate_qrcode(scooter_id):
    # Generiert QR-Code, der direkt auf die Rent-URL zeigt
    url = url_for('rent_scooter', scooter_id=scooter_id, _external=True)
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/rent/<int:scooter_id>')
@login_required
def rent_scooter(scooter_id):
    scooter = Scooter.query.get_or_404(scooter_id)
    if scooter.ist_verliehen:
        flash('Scooter ist bereits verliehen!', 'error')
    elif scooter.batterie_status < 20:
        flash('Batterie zu schwach!', 'error')
    else:
        scooter.ist_verliehen = True
        scooter.batterie_status -= 5 # Simulation Verbrauch
        db.session.commit()
        flash(f'{scooter.bezeichnung} erfolgreich ausgeliehen.', 'success')
    return redirect(url_for('index'))

@app.route('/add_scooter', methods=['POST'])
@login_required
def add_scooter():
    # Daten aus dem HTML-Formular holen
    bezeichnung = request.form.get('bezeichnung')
    standort = request.form.get('standort')
    batterie = request.form.get('batterie')

    # Einfache Validierung
    if not bezeichnung or not standort:
        flash('Bitte Bezeichnung und Standort angeben.', 'error')
        return redirect(url_for('index'))

    # Neuen Scooter erstellen
    neuer_scooter = Scooter(
        bezeichnung=bezeichnung,
        standort=standort,
        batterie_status=int(batterie) if batterie else 100
    )
    # In die Datenbank speichern
    db.session.add(neuer_scooter)
    db.session.commit()
    flash('Neuer Scooter wurde der Flotte hinzugefuegt!', 'success')
    return redirect(url_for('index'))

@app.route('/return/<int:scooter_id>')
@login_required
def return_scooter(scooter_id):
    scooter = Scooter.query.get_or_404(scooter_id)
    scooter.ist_verliehen = False
    db.session.commit()
    flash('Rueckgabe erfolgreich.', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email existiert bereits!')
            return redirect(url_for('register'))
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Login fehlgeschlagen.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/init_db')
def init_db():
    # Hilfs-Route um DB Tabellen zu erstellen und Testdaten einzufügen
    db.create_all()
    if not Scooter.query.first():
        s1 = Scooter(bezeichnung="City-Flitzer 1", standort="Bahnhof")
        s2 = Scooter(bezeichnung="E-Cruiser X", standort="Marktplatz", batterie_status=15)
        db.session.add_all([s1, s2])
        db.session.commit()
    return "Datenbank initialisiert!"

# --- API ROUTEN (REST) ---

@app.route('/api/scooters', methods=['GET'])
@require_api_key
def api_get_scooters():
    scooters = Scooter.query.all()
    return jsonify([s.to_dict() for s in scooters])

@app.route('/api/rent', methods=['POST'])
@require_api_key
def api_rent():
    data = request.get_json()
    scooter = Scooter.query.get(data.get('scooter_id'))
    if not scooter or scooter.ist_verliehen:
        return jsonify({'error': 'Nicht verfuegbar'}), 400
    scooter.ist_verliehen = True
    db.session.commit()
    return jsonify({'message': 'OK', 'scooter': scooter.to_dict()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
