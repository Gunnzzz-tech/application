from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright
import time

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- File upload setup ---
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/apply', methods=['POST'])
def apply():
    form = request.form
    file = request.files.get('resume')

    resume_filename = None
    file_path = None
    if file and file.filename:
        resume_filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
        file.save(file_path)

    # 1️⃣ Save to local DB
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

    # 2️⃣ Automatically submit to Website 1
    website1_form_url = "https://main-web-1.onrender.com/apply"      # Partner site form URL
    website1_thankyou_url = "https://main-web-1.onrender.com/success"

    website1_fields = {
        'input[name="first_name"]': form.get('first_name'),
        'input[name="last_name"]': form.get('last_name'),
        'input[name="email"]': form.get('email'),
        'input[name="phone"]': form.get('phone'),
        'input[name="country"]': form.get('country'),
        'input[name="city"]': form.get('city'),
        'input[name="address"]': form.get('address'),
        'input[name="position"]': form.get('position'),
        'textarea[name="additional_info"]': form.get('additional_info'),
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(website1_form_url, timeout=60000)

            # Fill text inputs
            text_fields = {
                'input[name="first_name"]': form.get('first_name'),
                'input[name="last_name"]': form.get('last_name'),
                'input[name="email"]': form.get('email'),
                'input[name="phone"]': form.get('phone'),
                'input[name="city"]': form.get('city'),
                'input[name="address"]': form.get('address'),
                'textarea[name="additional_info"]': form.get('additional_info')
            }
            for selector, value in text_fields.items():
                value = value or ""
                page.fill(selector, value)

            # Fill select inputs
            page.select_option('select[name="country"]', label=form.get('country'))
            page.select_option('select[name="position"]', label=form.get('position'))

            # Upload resume
            if file_path and os.path.exists(file_path):
                page.set_input_files('input[name="resume"]', file_path)

            # Submit form
            page.click('button[type="submit"]')

            # Wait for confirmation (optional)
            page.wait_for_selector(".success, .thank-you, #success-message", timeout=15000)
            browser.close()
            return redirect(website1_thankyou_url)
    except Exception as e:
        app.logger.error(f"Playwright automation failed: {e}")
        flash("Automation failed; your application is saved locally.")
        return redirect(url_for('index'))

@app.route('/applications')
def view_applications():
    apps = Application.query.order_by(Application.id.desc()).all()
    return render_template('applications.html', applications=apps)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
    #done