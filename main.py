import threading
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
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

# --- Database setup - SEPARATE DATABASE FOR L2 ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "applications.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- L2 Database Model ---
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
    submission_status = db.Column(db.String(50), default='pending')
    l1_submission_id = db.Column(db.String(100))
    submitted_at = db.Column(db.DateTime, server_default=db.func.now())


# Initialize database
with app.app_context():
    db.create_all()
    logger.info(f"✅ L2 connected to database: {DB_PATH}")


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


def submit_to_l1(application_id, preserved_params):
    """
    Background task to submit data to L1 (NO humanization delays)
    """
    try:
        # Get application from L2 database
        application = Application.query.get(application_id)
        if not application:
            logger.error(f"Application {application_id} not found")
            return

        logger.info(f"🔄 Submitting to L1 for application {application_id}")

        # Update status to processing
        application.submission_status = 'processing'
        db.session.commit()

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

        # Submit to L1 IMMEDIATELY (no delays)
        l1_submit_url = "https://velvelt.onrender.com/"

        # Add preserved parameters to payload
        l1_payload = {**form_data, **preserved_params}

        logger.info(f"🚀 Submitting to L1: {l1_submit_url}")
        response = requests.post(l1_submit_url, data=l1_payload, files=files, timeout=30)

        if files:
            files['resume'].close()

        logger.info(f"📡 L1 Response Status: {response.status_code}")

        if response.status_code in [200, 302]:
            logger.info(f"✅ Successfully submitted to L1: {application_id}")
            application.submission_status = 'completed'
            application.l1_submission_id = f"l1_{application_id}_{int(time.time())}"
        else:
            logger.warning(f"❌ L1 submission failed with status {response.status_code}")
            application.submission_status = 'failed'

        db.session.commit()

    except Exception as e:
        logger.error(f"💥 Error in L1 submission: {str(e)}")
        application = Application.query.get(application_id)
        if application:
            application.submission_status = 'error'
            db.session.commit()


# --- Routes ---
@app.route('/')
def index():
    """Show the application form"""
    preserved_params = get_preserved_params()
    return render_template('index.html', query_params=preserved_params)


@app.route('/apply', methods=['POST'])
def apply():
    """
    Process form submission:
    - Save to L2 database
    - Start background submission to L1
    - IMMEDIATELY redirect to L1's success page
    """
    try:
        form = request.form
        file = request.files.get('resume')

        # Save file locally
        resume_filename = None
        if file and file.filename:
            resume_filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
            file.save(file_path)
            logger.info(f"✅ File saved locally: {resume_filename}")

        # Save to L2 database
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
            resume_filename=resume_filename,
            submission_status='pending'
        )
        db.session.add(application)
        db.session.commit()

        logger.info(f"✅ Application saved to L2 database with ID: {application.id}")

        preserved_params = get_preserved_params()

        # 🚀 Start background submission to L1 (user doesn't wait)
        thread = threading.Thread(
            target=submit_to_l1,
            args=(application.id, preserved_params),
            daemon=True
        )
        thread.start()

        logger.info(f"🚀 Started background L1 submission for application {application.id}")

        # ⚡ IMMEDIATE redirect to L1's success page
        l1_success_url = build_redirect_url("https://velvelt.onrender.com/submit")

        logger.info(f"📍 Immediate redirect to L1 success page: {l1_success_url}")
        return redirect(l1_success_url)

    except Exception as e:
        logger.error(f"❌ Error processing application: {str(e)}")
        db.session.rollback()
        flash('Error submitting application. Please try again.', 'error')
        return redirect(url_for('index'))


@app.route('/status')
def status():
    """Check submission status"""
    total = Application.query.count()
    pending = Application.query.filter_by(submission_status='pending').count()
    processing = Application.query.filter_by(submission_status='processing').count()
    completed = Application.query.filter_by(submission_status='completed').count()
    failed = Application.query.filter_by(submission_status='failed').count()
    error = Application.query.filter_by(submission_status='error').count()

    return jsonify({
        'total_applications': total,
        'pending_submissions': pending,
        'processing_submissions': processing,
        'completed_submissions': completed,
        'failed_submissions': failed,
        'error_submissions': error,
        'database': DB_PATH
    })


if __name__ == '__main__':
    logger.info("🚀 Starting L2 Server...")
    logger.info(f"📊 Using L2 database: {DB_PATH}")
    logger.info("⚡ Instant redirect to L1 configured")
    app.run(debug=True, host='0.0.0.0', port=5000)