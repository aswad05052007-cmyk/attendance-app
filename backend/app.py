from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import sqlite3
import qrcode
import os
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)
CORS(app)

# ---------- DB ----------
def init_db():
    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS students(id TEXT PRIMARY KEY, name TEXT, pass TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS attendance(id TEXT, date TEXT)")

    conn.commit()
    conn.close()

init_db()

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# ---------- FRONTEND ROUTES (FINAL FIX) ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

@app.route('/')
def home():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/admin')
def admin_page():
    return send_from_directory(FRONTEND_DIR, 'admin.html')

@app.route('/student')
def student_page():
    return send_from_directory(FRONTEND_DIR, 'student.html')

# ---------- LOGIN ----------
@app.route("/login", methods=["POST"])
def login():
    d = request.json
    user = d["user"].strip()
    password = d["password"].strip()

    if user == ADMIN_USER and password == ADMIN_PASS:
        return jsonify({"role": "admin"})

    conn = sqlite3.connect("db.db")
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE id=? AND pass=?", (user, password))
    s = c.fetchone()
    conn.close()

    if s:
        return jsonify({"role": "student", "id": user})

    return jsonify({"error": "Invalid login"})

# ---------- ADD STUDENT ----------
@app.route("/add", methods=["POST"])
def add():
    d = request.json
    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    try:
        c.execute("INSERT INTO students VALUES(?,?,?)",
                  (d["id"].strip(), d["name"].strip(), d["pass"].strip()))
        conn.commit()
    except:
        return jsonify({"msg": "ID already exists ❌"})

    conn.close()
    return jsonify({"msg": "Student Added ✅"})

# ---------- QR ----------
@app.route("/qr")
def qr():
    expiry = datetime.now() + timedelta(seconds=60)
    value = str(expiry.timestamp())

    if not os.path.exists("static"):
        os.makedirs("static")

    img = qrcode.make(value)
    img.save("static/qr.png")

    return jsonify({"img": "/static/qr.png", "exp": expiry.timestamp(), "val": value})

# ---------- MARK ----------
@app.route("/mark", methods=["POST"])
def mark():
    d = request.json
    student = d["id"]
    qr = d["qr"]

    if float(qr) < datetime.now().timestamp():
        return jsonify({"msg": "QR Expired ❌"})

    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("SELECT * FROM attendance WHERE id=? AND date=?", (student, today))
    if c.fetchone():
        return jsonify({"msg": "Already Marked ❌"})

    c.execute("INSERT INTO attendance VALUES(?,?)", (student, today))
    conn.commit()
    conn.close()

    return jsonify({"msg": "Attendance Marked ✅"})

# ---------- STATS ----------
@app.route("/stats")
def stats():
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM attendance WHERE date=?", (today,))
    present = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM students")
    total = c.fetchone()[0]

    conn.close()

    return jsonify({"total": total, "present": present, "absent": total - present})

# ---------- HISTORY ----------
@app.route("/history/<id>")
def history(id):
    conn = sqlite3.connect("db.db")
    c = conn.cursor()

    c.execute("SELECT * FROM attendance WHERE id=?", (id,))
    data = c.fetchall()

    conn.close()
    return jsonify(data)

# ---------- EXPORT ----------
@app.route("/export")
def export():
    conn = sqlite3.connect("db.db")
    df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()

    file = "attendance.xlsx"
    df.to_excel(file, index=False)

    return send_file(
        file,
        as_attachment=True,
        download_name="attendance.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)