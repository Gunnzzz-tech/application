import threading
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
import time
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- File upload setup ---
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Database setup - USE SAME DATABASE AS L1 ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)
DB_PATH = os.path.join(INSTANCE_DIR, "job_portal.db")  # Same DB as L1
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- Use the EXACT SAME Model as L1 ---
class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    address = db.Column(db.String(255))
    position = db.Column(db.String(100))
    additional_info = db.Column(db.Text)
    resume_filename = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime, server_default=db.func.now())
    source = db.Column(db.String(50), default='direct')
    ip_address = db.Column(db.String(50))


# Initialize database
with app.app_context():
    db.create_all()
    logger.info(f"✅ Bot connected to L1 database: {DB_PATH}")


# --- Helper functions ---
def get_preserved_params():
    params = {}
    for key, value in request.args.items():
        if key.startswith('utm_') or key == 'gclid' or key == 'fbclid':
            params[key] = value
    return params


def build_redirect_url(base_url, extra_params=None):
    params = get_preserved_params()
    if extra_params:
        params.update(extra_params)
    if params:
        return f"{base_url}?{urlencode(params)}"
    return base_url


# --- Humanized submission functions ---
def simulate_human_typing(text, field_name):
    """Simulate human typing speed with variations"""
    if not text:
        return
    time_per_char = random.uniform(0.08, 0.15)
    if field_name in ['additional_info', 'address']:
        time_per_char *= 0.7
    time.sleep(len(text) * time_per_char)


def submit_to_l1_humanized(application_id, preserved_params):
    """
    Background task to submit data to L1 with human-like behavior
    """
    try:
        # Get application from database
        application = Applicant.query.get(application_id)
        if not application:
            logger.error(f"Application {application_id} not found")
            return False

        logger.info(f"🔄 Starting humanized L1 submission for application {application_id}")

        # Prepare form data for L1
        form_data = {
            'first_name': application.first_name,
            'last_name': application.last_name,
            'email': application.email,
            'phone': application.phone,
            'country': application.country,
            'city': application.city,
            'address': application.address,
            'position': application.position,
            'additional_info': application.additional_info
        }

        # Handle file upload
        files = None
        if application.resume_filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], application.resume_filename)
            if os.path.exists(file_path):
                files = {'resume': open(file_path, 'rb')}
                logger.info(f"📎 Attaching file: {application.resume_filename}")

        # Submit to L1
        l1_submit_url = "https://velvelt.onrender.com/"

        logger.info(f"🚀 Submitting to L1: {l1_submit_url}")
        logger.info(f"📦 Form data keys: {list(form_data.keys())}")

        # Make the POST request
        response = requests.post(l1_submit_url, data=form_data, files=files, timeout=30)

        if files:
            files['resume'].close()

        logger.info(f"📡 L1 Response Status: {response.status_code}")
        logger.info(f"📡 L1 Response URL: {response.url}")

        if response.status_code in [200, 302] and 'submit' in response.url:
            logger.info(f"✅ Successfully submitted to L1: {application_id}")
            return True
        else:
            logger.warning(f"❌ L1 submission failed with status {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"💥 Error in L1 submission: {str(e)}")
        return False


# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            form = request.form
            file = request.files.get('resume')

            resume_filename = None
            if file and file.filename:
                resume_filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
                file.save(file_path)
                logger.info(f"✅ File saved locally: {resume_filename}")

            # Save to the same database as L1
            applicant = Applicant(
                first_name=form.get('first_name'),
                last_name=form.get('last_name'),
                email=form.get('email'),
                phone=form.get('phone'),
                country=form.get('country'),
                city=form.get('city'),
                address=form.get('address'),
                position=form.get('position'),
                additional_info=form.get('additional_info'),
                resume_filename=resume_filename,
                source='bot'  # Mark as bot submission
            )
            db.session.add(applicant)
            db.session.commit()

            logger.info(f"✅ Application saved to database with ID: {applicant.id}")

            preserved_params = get_preserved_params()

            # Start background processing to submit to L1
            thread = threading.Thread(
                target=submit_to_l1_humanized,
                args=(applicant.id, preserved_params),
                daemon=True
            )
            thread.start()

            logger.info(f"🚀 Started background L1 submission for application {applicant.id}")

            # Immediate redirect to L1's success page
            base_redirect_url = "https://velvelt.onrender.com/submit"
            redirect_url = build_redirect_url(base_redirect_url)

            logger.info(f"📍 Immediate redirect to: {redirect_url}")
            return redirect(redirect_url)

        except Exception as e:
            logger.error(f"❌ Error processing application: {str(e)}")
            db.session.rollback()
            flash('Error submitting application. Please try again.', 'error')
            preserved_params = get_preserved_params()
            return render_template('index.html', query_params=preserved_params)

    preserved_params = get_preserved_params()
    return render_template('index.html', query_params=preserved_params)


@app.route('/status')
def status():
    """Check submission status"""
    total = Applicant.query.count()
    bot_subs = Applicant.query.filter_by(source='bot').count()
    direct_subs = Applicant.query.filter_by(source='direct').count()

    return jsonify({
        'total_applications': total,
        'bot_submissions': bot_subs,
        'direct_submissions': direct_subs,
        'database': DB_PATH
    })


if __name__ == '__main__':
    logger.info("🚀 Starting L2 Bot Server...")
    logger.info(f"📊 Using shared database: {DB_PATH}")
    app.run(debug=True, port=5001)