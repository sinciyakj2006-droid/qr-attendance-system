import os
import io
import base64
import datetime
from flask import Flask, request, render_template_string, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import jwt
import qrcode

app = Flask(__name__)

# Secret key configuration for cryptographic token signing
app.config['SECRET_KEY'] = 'MySecretLaptopKey123!'

# Fallback to local SQLite if DATABASE_URL environment variable isn't defined on Render
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///local_attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Create tables if they do not exist
with app.app_context():
    db.create_all()

# Single-file HTML User Interface Template with responsive columns
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QR Attendance System</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f7fafc; margin: 0; padding: 20px; color: #2d3748; }
        .container { max-width: 1200px; margin: auto; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #4a5568; }
        h2 { margin-top: 0; color: #4a5568; font-size: 1.4rem; border-bottom: 2px solid #edf2f7; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 0.9rem; }
        input[type="text"], input[type="password"], select { width: 100%; padding: 10px; border: 1px solid #cbd5e0; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background-color: #4a5568; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #2d3748; }
        .token-box { color: red; word-break: break-all; cursor: pointer; background: #fff5f5; padding: 12px; border: 1px dashed red; border-radius: 4px; font-family: monospace; font-size: 0.85rem; margin-top: 10px; }
        .copy-btn { margin-top: 8px; padding: 6px 12px; background-color: #718096; font-size: 0.8rem; }
        .copy-btn:hover { background-color: #4a5568; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.9rem; }
        th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: left; }
        th { background-color: #f7fafc; }
    </style>
</head>
<body>
    <h1 style="text-align: center; color: #2d3748; margin-bottom: 30px;">QR Attendance Management Dashboard</h1>
    <div class="container">
        
        <div class="card">
            <h2>1. Register Profile</h2>
            <form action="/register" method="POST">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" name="username" required placeholder="e.g., instructor1">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" required placeholder="••••••••">
                </div>
                <div class="form-group">
                    <label>Role Account Type</label>
                    <select name="role">
                        <option value="Admin">Admin / Teacher</option>
                        <option value="Student">Student</option>
                    </select>
                </div>
                <button type="submit">Create Profile Account</button>
            </form>
        </div>

        <div class="card">
            <h2>2. Admin: Generate QR</h2>
            <form action="/generate-qr" method="POST">
                <div class="form-group">
                    <label>Session or Class ID</label>
                    <input type="text" name="session_id" required placeholder="e.g., CS102">
                </div>
                <button type="submit">Generate Code</button>
            </form>
            
            {% if qr_img %}
                <div style="text-align: center; margin-top: 20px;">
                    <img src="data:image/png;base64,{{ qr_img }}" alt="Generated Dynamic QR Code" style="border: 1px solid #e2e8f0; padding: 5px; background: white; max-width: 180px;">
                </div>
                <p id="tokenText" class="token-box" onclick="window.getSelection().selectAllChildren(this);" title="Click to highlight string text automatically">Token: {{ token }}</p>
                <button type="button" class="copy-btn" onclick="copyTokenText()">📋 Copy Full Token String</button>
            {% endif %}
        </div>

        <div class="card">
            <h2>3. Student: Submit Token</h2>
            <form action="/scan-qr" method="POST">
                <div class="form-group">
                    <label>Student Name</label>
                    <input type="text" name="student_name" required placeholder="Enter your full name">
                </div>
                <div class="form-group">
                    <label>Decoded QR Token String</label>
                    <input type="text" name="token" required placeholder="Paste the encrypted token text string here">
                </div>
                <button type="submit" style="background-color: #38a169;">Submit Attendance Record</button>
            </form>
        </div>

    </div>

    <div style="max-width: 1200px; margin: 30px auto 0 auto;" class="card">
        <h2>Live System Production Attendance Registry Logs</h2>
        <table>
            <thead>
                <tr>
                    <th>Log Reference ID</th>
                    <th>Student Name Logged</th>
                    <th>Verified Session Code</th>
                    <th>Server Log Timestamp (UTC)</th>
                </tr>
            </thead>
            <tbody>
                {% for log in logs %}
                <tr>
                    <td>{{ log.id }}</td>
                    <td>{{ log.student_name }}</td>
                    <td>{{ log.session_id }}</td>
                    <td>{{ log.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="4" style="text-align: center; color: #a0aec0;">No attendance check-ins recorded yet in this cloud session.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <script>
    function copyTokenText() {
        var pText = document.getElementById("tokenText").innerText;
        var cleanToken = pText.replace("Token: ", "").trim();
        
        navigator.clipboard.writeText(cleanToken).then(function() {
            alert("Token copied cleanly to clipboard! Paste it directly into Column 3.");
        }).catch(function(err) {
            alert("Browser blocked auto-copy. Please click inside the red box and press Ctrl+A then Ctrl+C.");
        });
    }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    logs = Attendance.query.all()
    return render_template_string(HTML_TEMPLATE, logs=logs)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return '<script>alert("User profile registered successfully!"); window.location="/";</script>'
    return redirect(url_for('index'))

@app.route('/generate-qr', methods=['POST'])
def generate_qr():
    session_id = request.form.get('session_id')
    
    # Token expiration configuration set safely to 10 minutes to allow easy human copy-paste validation
    token = jwt.encode({
        'session_id': session_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
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

@app.route('/scan-qr', methods=['GET', 'POST'])
def scan_qr():
    if request.method == 'POST':
        # Safety fallback to capture variations of layout inputs
        raw_token = request.form.get('token') or request.form.get('qr_token') or request.form.get('tokenText')
        
        if not raw_token:
            return '<script>alert("Error: No token received from the web form."); window.location="/";</script>'
            
        token = raw_token.strip()
        student_name = request.form.get('student_name') or request.form.get('username') or "Student"
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            session_id = payload['session_id']
            
            # Dual-column schema validation fallback layer
            try:
                new_log = Attendance(student_name=student_name, session_id=session_id)
            except TypeError:
                new_log = Attendance(username=student_name, session_id=session_id)
                
            db.session.add(new_log)
            db.session.commit()
            return '<script>alert("Attendance Marked Successfully!"); window.location="/";</script>'
        except jwt.ExpiredSignatureError:
            return '<script>alert("SECURITY BOUNDARY ENFORCED: This QR token has expired!"); window.location="/";</script>'
        except jwt.InvalidTokenError:
            return '<script>alert("SECURITY BREAK: Malicious or altered token signature detected."); window.location="/";</script>'
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Binds dynamically to production environment configurations 
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)