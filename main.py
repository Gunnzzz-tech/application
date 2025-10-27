import requests
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from urllib.parse import urlencode, parse_qs

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


# --- Helper functions for parameter preservation ---
def get_preserved_params():
    """
    Extract and return only UTM and GCLID parameters from request
    """
    params = {}
    for key, value in request.args.items():
        if key.startswith('utm_') or key == 'gclid' or key == 'fbclid':
            params[key] = value
    return params


def build_redirect_url(base_url, extra_params=None):
    """
    Build a redirect URL with preserved UTM/GCLID parameters
    """
    params = get_preserved_params()

    # Add any extra parameters if provided
    if extra_params:
        params.update(extra_params)

    # Build the final URL
    if params:
        return f"{base_url}?{urlencode(params)}"
    return base_url


# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form = request.form
        file = request.files.get('resume')

        resume_filename = None
        file_path = None
        if file and file.filename:
            resume_filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
            file.save(file_path)

        # Save locally
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

        # Forward to Website 1 (L1) WITH preserved parameters
        website1_form_url = "https://velvelt.onrender.com/"

        # ✅ PRESERVE PARAMETERS when forwarding to L1
        preserved_params = get_preserved_params()
        if preserved_params:
            website1_form_url = f"{website1_form_url}?{urlencode(preserved_params)}"

        form_data = {
            "first_name": form.get("first_name"),
            "last_name": form.get("last_name"),
            "email": form.get("email"),
            "phone": form.get("phone"),
            "country": form.get("country"),
            "city": form.get("city"),
            "address": form.get("address"),
            "position": form.get("position"),
            "additional_info": form.get("additional_info"),
            "terms1": form.get("terms1", "on"),
            "terms2": form.get("terms2", "on"),
            "terms3": form.get("terms3", "on"),
        }

        form_data.update(preserved_params)

        files = {"resume": open(file_path, "rb")} if file_path else None

        try:
            resp = requests.post(website1_form_url, data=form_data, files=files, timeout=30)
            if resp.status_code in [200, 302]:
                app.logger.info("Successfully sent to Website 1")
                app.logger.info(f"Preserved parameters: {preserved_params}")
            else:
                app.logger.warning(f"Website 1 submission failed with status {resp.status_code}")
        except Exception as e:
            app.logger.error(f"Website 1 submission failed: {e}")
        finally:
            if files:
                files["resume"].close()

        # ✅ Redirect to Website 1 `/submit` page WITH original query params
        base_redirect_url = "https://velvelt.onrender.com/submit"
        redirect_url = build_redirect_url(base_redirect_url)

        app.logger.info(f"Redirecting to: {redirect_url}")
        return redirect(redirect_url)

    # GET request → render form with preserved parameters
    preserved_params = get_preserved_params()
    return render_template('index.html', query_params=preserved_params)


@app.route('/terms/data-collection')
def terms_data_collection():
    preserved_params = get_preserved_params()
    return render_template('terms_data_collection.html', query_params=preserved_params)


@app.route('/terms/communication')
def terms_communication():
    preserved_params = get_preserved_params()
    return render_template('terms_communication.html', query_params=preserved_params)


@app.route('/terms/recruitment')
def terms_recruitment():
    preserved_params = get_preserved_params()
    return render_template('terms_recruitment.html', query_params=preserved_params)


@app.route('/applications')
def view_applications():
    apps = Application.query.order_by(Application.id.desc()).all()
    preserved_params = get_preserved_params()  # gclid, utm_

    # Build a query string for template links
    query_string = urlencode(preserved_params) if preserved_params else ''

    return render_template(
        'applications.html',
        applications=apps,
        query_params=preserved_params,
        query_string=query_string
    )


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ✅ ADDITIONAL ROUTE FOR L1 COMPATIBILITY
@app.route('/submit')
def submit_redirect():
    """
    Redirect to L1's /submit with preserved query parameters
    """
    base_redirect_url = "https://velvelt.onrender.com/submit?gclid=Cj0KCQjw2uiwBhCXARIsACMvIU0FJgVvVA7dG6hSAWQ1JZR32KJvUzHssC4gqiH5_789defABC123dummy&utm_source=google&utm_medium=cpc&utm_campaign=spring_sale&utm_id=promo_2024&utm_term=test+keyword&utm_content=textlink_v2"
    # Pass current request args to build_redirect_url
    redirect_url = build_redirect_url(base_redirect_url)
    return redirect(redirect_url)

if __name__ == '__main__':
    app.run(debug=True)