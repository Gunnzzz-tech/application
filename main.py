from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- File upload setup (move inside static for public access) ---
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Database setup ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///applications.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Model ---
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    address = db.Column(db.String(255))
    position = db.Column(db.String(100))
    additional_info = db.Column(db.Text)
    resume_filename = db.Column(db.String(255))

with app.app_context():
    db.create_all()

# --- Routes ---

# Home page / form
@app.route('/')
def index():
    return render_template('index.html')

# Form submission
@app.route('/apply', methods=['POST'])
def apply():
    form = request.form
    file = request.files.get('resume')

    resume_filename = None
    if file and file.filename:
        resume_filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))

    # Save to DB
    application = Application(
        first_name=form.get('first_name'),
        last_name=form.get('last_name'),
        email=form.get('email'),
        phone=form.get('phone'),
        country=form.get('country'),
        city=form.get('city'),
        address=form.get('address'),
        position=form.get('position'),
        additional_info=form.get('additional_info'),
        resume_filename=resume_filename
    )
    db.session.add(application)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Application submitted successfully!'})

# Dashboard / view all submissions
@app.route('/applications')
def view_applications():
    apps = Application.query.order_by(Application.id.desc()).all()
    return render_template('applications.html', applications=apps)

# Serve uploaded resumes
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Run app ---
if __name__ == '__main__':
    app.run(debug=True)
