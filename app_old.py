import os
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime
from werkzeug.security import check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

# Configuration
os.environ['VERIFY_TOKEN'] = 'Tevkil2024_Secure_Webhook_9x7mN2p'
os.environ['ACCESS_TOKEN'] = 'EAAUtDMHauXgBPs7tcGiVUZB3IAee8ZANmgxLbPjXQQhUL6S6dZBpNbpBn3YMoQ6uoecD8H4ZCMj3OMwsuZBrstg9EXTjkE1hpGlfOBwpPFCkomWEFsNGsZABqekRl2mlrnEkVPghmxZAzjLc6xU8a1rt1tcURU5tRja2vZB6oZBePgvZAkL3Y7HCrJToZAzhEN8BdmYkFWPSIlIOFaZB2rtzOtFBu3V316AZAKH9oMONeZBMGkVQphjwZDZD'

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Session secret key

# Flask-Login ayarları
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Kullanıcı sınıfı
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Veritabanı bağlantısı
def get_db_connection():
    conn = sqlite3.connect('tevkil.db')
    conn.row_factory = sqlite3.Row
    return conn

# Kullanıcı yükleme
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'])
    return None

# Ana sayfa
@app.route("/")
def index():
    return "Sistem çalışıyor! Webhook hazır. Tevkil projesi devam ediyor. 🎉"

# Login sayfası
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username']))
            return redirect(url_for("list_ilans"))
        else:
            return "Hatalı kullanıcı adı veya şifre", 401
    return render_template("login.html")

# Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# Meta webhook doğrulama
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        return challenge, 200
    else:
        print(f"Verification failed: mode={mode}, token={token}, expected={VERIFY_TOKEN}")
        return "Verification failed", 403

# WhatsApp mesajları
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Gelen veri:", data)

    if data and "entry" in data:
        conn = get_db_connection()
        cursor = conn.cursor()

        for entry in data["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for message in messages:
                    sender = message["from"]
                    text = message["text"]["body"]
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    print(f"Mesaj geldi: {sender} - {text}")
                    cursor.execute(
                        "INSERT INTO ilans (sender, message, timestamp) VALUES (?, ?, ?)",
                        (sender, text, timestamp)
                    )

        conn.commit()
        conn.close()
    return "EVENT_RECEIVED", 200

# İlanları listele
@app.route("/ilans")
@login_required
def list_ilans():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ilans ORDER BY timestamp DESC")
    ilans = cursor.fetchall()
    conn.close()
    return render_template("ilans.html", ilans=ilans)

if __name__ == "__main__":
    app.run(port=5000, debug=True)