import threading
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
import logging
import time
import random
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
def submit_to_l1_humanized(application_id, preserved_params):
    """
    Background task to submit data to L1 with realistic human behavior
    User is already redirected to success page - this runs in background
    """
    try:
        # Create application context for the thread
        with app.app_context():
            # Get application from L2 database
            application = Application.query.get(application_id)
            if not application:
                logger.error(f"Application {application_id} not found")
                return

            logger.info(f"🔄 Starting HUMANIZED submission for application {application_id}")

            # Update status to processing
            application.submission_status = 'processing'
            db.session.commit()

            # Step 1: Initial page load simulation (2-4 seconds)
            logger.info("⏳ Simulating page load and initial orientation...")
            time.sleep(random.uniform(2, 4))

            # Step 2: Simulate scrolling and reading the form
            logger.info("📄 Simulating form scanning...")
            time.sleep(random.uniform(3, 6))

            # Step 3: Fill form fields with realistic timing
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

            # Simulate filling each field with human-like behavior
            logger.info("⌨️  Simulating form filling...")

            # Personal Information section
            simulate_field_filling('first_name', application.first_name, 'name')
            simulate_field_filling('last_name', application.last_name, 'name')
            simulate_field_filling('email', application.email, 'email')
            simulate_field_filling('phone', application.phone, 'phone')

            # Location section
            simulate_field_filling('country', application.country, 'dropdown')
            simulate_field_filling('city', application.city, 'name')
            simulate_field_filling('address', application.address, 'address')

            # Position section
            simulate_field_filling('position', application.position, 'dropdown')
            simulate_field_filling('additional_info', application.additional_info, 'textarea')

            # Step 4: File upload consideration
            if application.resume_filename:
                logger.info("📎 Simulating file upload consideration...")
                time.sleep(random.uniform(2, 4))
                # Simulate file selection delay
                time.sleep(random.uniform(1, 2))

            # Step 5: Terms and conditions reading simulation
            logger.info("📖 Simulating terms and conditions reading...")
            # Simulate reading each terms section
            terms_sections = 3
            for i in range(terms_sections):
                logger.info(f"   Reading terms section {i + 1}/{terms_sections}...")
                # Simulate reading time per section (3-8 seconds each)
                time.sleep(random.uniform(3, 8))
                # Simulate scrolling between sections
                if i < terms_sections - 1:
                    time.sleep(random.uniform(1, 2))

            # Step 6: Checkbox interactions
            logger.info("✅ Simulating checkbox interactions...")
            for i in range(3):  # 3 terms checkboxes
                time.sleep(random.uniform(0.5, 1.5))
                # Random chance of unchecking and rechecking (human hesitation)
                if random.random() < 0.2:
                    time.sleep(random.uniform(0.5, 1))
                    logger.info("   🤔 Reconsidering terms...")

            # Step 7: Final review before submission
            logger.info("🔍 Simulating final form review...")
            time.sleep(random.uniform(4, 8))

            # Random chance of making a small correction
            if random.random() < 0.3:
                logger.info("   ✏️  Making a small correction...")
                time.sleep(random.uniform(2, 4))

            # Step 8: Hover and hesitation before submit
            logger.info("🤔 Hesitating before submission...")
            time.sleep(random.uniform(1, 3))

            # Step 9: Submit to L1
            logger.info("🚀 Submitting to L1...")

            # Prepare payload for L1
            l1_payload = {**form_data, **preserved_params}

            # Handle file upload
            files = None
            if application.resume_filename:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], application.resume_filename)
                if os.path.exists(file_path):
                    files = {'resume': open(file_path, 'rb')}
                    logger.info(f"📎 Attaching file: {application.resume_filename}")

            # Submit to L1
            l1_submit_url = "https://velvelt.onrender.com/"
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
        logger.error(f"💥 Error in humanized L1 submission: {str(e)}")
        # Try to update status even if there's an error
        try:
            with app.app_context():
                application = Application.query.get(application_id)
                if application:
                    application.submission_status = 'error'
                    db.session.commit()
        except Exception as inner_e:
            logger.error(f"💥 Could not update error status: {inner_e}")


def simulate_field_filling(field_name, value, field_type):
    """
    Simulate realistic field filling behavior
    """
    if not value:
        return

    logger.info(f"   Filling {field_name.replace('_', ' ')}...")

    # Different behaviors for different field types
    if field_type == 'name':
        # Names are typed quickly but with occasional pauses
        time.sleep(random.uniform(0.5, 1.5))
        simulate_typing(value, 'fast')

    elif field_type == 'email':
        # Emails are typed quickly (people know their emails well)
        time.sleep(random.uniform(0.3, 1.0))
        simulate_typing(value, 'fast')

    elif field_type == 'phone':
        # Phone numbers with pauses between groups
        time.sleep(random.uniform(0.8, 1.8))
        simulate_typing(value, 'numbers')

    elif field_type == 'dropdown':
        # Dropdown selection with reading time
        time.sleep(random.uniform(1.5, 3.0))

    elif field_type == 'address':
        # Address typing with thinking time
        time.sleep(random.uniform(1.0, 2.0))
        simulate_typing(value, 'medium')

    elif field_type == 'textarea':
        # Text areas with lots of thinking and editing
        time.sleep(random.uniform(2.0, 4.0))
        simulate_typing(value, 'slow')

    # Small pause after each field
    time.sleep(random.uniform(0.2, 0.8))


def simulate_typing(text, speed='medium'):
    """
    Simulate realistic typing with variable speed
    """
    if not text:
        return

    # Define typing speeds (seconds per character)
    speed_config = {
        'fast': (0.05, 0.12),
        'medium': (0.08, 0.18),
        'slow': (0.12, 0.25),
        'numbers': (0.06, 0.15)
    }

    min_delay, max_delay = speed_config.get(speed, (0.08, 0.18))

    for i, char in enumerate(text):
        # Base typing delay
        time_per_char = random.uniform(min_delay, max_delay)
        time.sleep(time_per_char)

        # Occasional longer pauses (thinking, correcting)
        if random.random() < 0.03:  # 3% chance of longer pause
            time.sleep(random.uniform(0.3, 0.8))

        # Pause between words
        if char == ' ' and random.random() < 0.4:
            time.sleep(random.uniform(0.1, 0.3))

        # Occasional backspacing and retyping (typos)
        if random.random() < 0.02 and i > 2:  # 2% chance of typo correction
            time.sleep(random.uniform(0.2, 0.5))
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
        # Create application context for the thread
        with app.app_context():
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
        # Try to update status even if there's an error
        try:
            with app.app_context():
                application = Application.query.get(application_id)
                if application:
                    application.submission_status = 'error'
                    db.session.commit()
        except Exception as inner_e:
            logger.error(f"💥 Could not update error status: {inner_e}")

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
    - Start HUMANIZED background submission to L1
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

        # 🚀 Start HUMANIZED background submission to L1
        thread = threading.Thread(
            target=submit_to_l1_humanized,  # Changed to humanized version
            args=(application.id, preserved_params),
            daemon=True
        )
        thread.start()

        logger.info(f"🤖 Started HUMANIZED L1 submission for application {application.id}")

        # ⚡ IMMEDIATE redirect to L1's success page (user doesn't wait!)
        l1_success_url = build_redirect_url("https://velvelt.onrender.com/submit")

        logger.info(f"📍 Immediate redirect to L1 success page: {l1_success_url}")
        return redirect(l1_success_url)

    except Exception as e:
        logger.error(f"❌ Error processing application: {str(e)}")
        db.session.rollback()
        flash('Error submitting application. Please try again.', 'error')
        return redirect(url_for('index'))
@app.route('/applications')
def applications():
    """View all submitted applications in L2"""
    try:
        # Get all applications ordered by most recent
        all_applications = Application.query.order_by(Application.submitted_at.desc()).all()

        # Get status summary
        status_summary = {
            'total': Application.query.count(),
            'pending': Application.query.filter_by(submission_status='pending').count(),
            'processing': Application.query.filter_by(submission_status='processing').count(),
            'completed': Application.query.filter_by(submission_status='completed').count(),
            'failed': Application.query.filter_by(submission_status='failed').count(),
            'error': Application.query.filter_by(submission_status='error').count()
        }

        logger.info(f"📊 Applications page accessed - Total: {status_summary['total']}")

        return render_template('applications.html',
                               applications=all_applications,
                               status_summary=status_summary)

    except Exception as e:
        logger.error(f"❌ Error loading applications: {str(e)}")
        flash('Error loading applications.', 'error')
        return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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