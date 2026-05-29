import os
import datetime
import jwt
import qrcode
import io
import base64
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)

# Local development security configurations
app.config['SECRET_KEY'] = 'MySecretLaptopKey123!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local_attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Database Architecture Schemas
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # Roles: 'Admin' or 'Student'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(50), nullable=False)
    session_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QR Attendance System</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f4f6f9; text-align: center;}
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-block; margin: 20px; vertical-align: top; width: 300px;}
        input, select, button { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #28a745; color: white; border: none; cursor: pointer; font-weight: bold;}
        button:hover { background: #218838; }
    </style>
</head>
<body>
    <h1>QR Attendance Management System</h1>
    
    <div class="card">
        <h3>1. Register Account</h3>
        <form action="/register" method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <select name="role">
                <option value="Student">Student</option>
                <option value="Admin">Admin (Instructor)</option>
            </select>
            <button type="submit">Create Account</button>
        </form>
    </div>

    <div class="card">
        <h3>2. Admin: Generate QR</h3>
        <form action="/generate-qr" method="POST">
            <input type="text" name="session_id" placeholder="Session Code (e.g. CS101)" required>
            <button type="submit" style="background: #007bff;">Generate Code</button>
        </form>
        {% if qr_img %}
            <h4>Scan This Code:</h4>
            <img src="data:image/png;base64,{{ qr_img }}" width="200">
            <p style="font-size:11px; color:red; word-break: break-all;">Token: {{ token[:60] }}...</p>
        {% endif %}
    </div>

    <div class="card">
        <h3>3. Student: Submit Token</h3>
        <form action="/scan-qr" method="POST">
            <input type="text" name="username" placeholder="Confirm Student Username" required>
            <input type="text" name="qr_token" placeholder="Paste QR Token text string here" required>
            <button type="submit" style="background: #ffc107; color: black;">Submit Attendance</button>
        </form>
    </div>

    <div style="margin-top: 30px;">
        <h3>Active Attendance Registry Log:</h3>
        <table border="1" align="center" cellpadding="10" style="background:white; border-collapse:collapse; width:60%;">
            <tr style="background:#eee;"><th>ID</th><th>Student</th><th>Session ID</th><th>Timestamp (UTC)</th></tr>
            {% for log in logs %}
            <tr><td>{{ log.id }}</td><td>{{ log.student_name }}</td><td>{{ log.session_id }}</td><td>{{ log.timestamp }}</td></tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    logs = Attendance.query.all()
    return render_template_string(HTML_TEMPLATE, logs=logs, qr_img=None)

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password_hash=hashed, role=role)
    db.session.add(new_user)
    db.session.commit()
    return '<script>alert("User profile registered!"); window.location="/";</script>'

@app.route('/generate-qr', methods=['POST'])
def generate_qr():
    session_id = request.form.get('session_id')
    token = jwt.encode({
        'session_id': session_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    logs = Attendance.query.all()
    return render_template_string(HTML_TEMPLATE, logs=logs, qr_img=qr_b64, token=token)

@app.route('/scan-qr', methods=['GET','POST'])
def scan_qr():
    if request.method == 'POST':
    token = request.form.get('token').strip()
    try:
        payload = jwt.decode(qr_token, app.config['SECRET_KEY'], algorithms=['HS256'])
        session_id = payload['session_id']
        new_log = Attendance(student_name=username, session_id=session_id)
        db.session.add(new_log)
        db.session.commit()
        return '<script>alert("Attendance Marked Successfully!"); window.location="/";</script>'
    except jwt.ExpiredSignatureError:
        return '<script>alert("SECURITY BOUNDARY ENFORCED: This QR token has expired! It is past its 60-second validity window."); window.location="/";</script>'
    except jwt.InvalidTokenError:
        return '<script>alert("SECURITY BREAK: Malicious or altered token signature detected."); window.location="/";</script>'

if __name__ == '__main__':

    import os

    port = int(os.environ.get("PORT", 5000))

    app.run(host='0.0.0.0', port=port)