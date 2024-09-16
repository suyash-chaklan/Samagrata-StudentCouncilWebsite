import flask
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate  # Import Migrate for database migrations
from sqlalchemy.orm import DeclarativeBase
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy.orm import Mapped, mapped_column
import json
import sqlite3
from dotenv import load_dotenv
import os
import csv
from io import StringIO
from flask import Response


def configure():
    load_dotenv()


configure()
local_server = True
with open('templates/config.json', 'r') as c:
    params = json.load(c)["params"]


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
app = Flask(__name__, static_folder='static')
admin = Admin()
admin.init_app(app)

# Flask-Migrate setup
migrate = Migrate(app, db)

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=os.getenv('GMAIL_PASSWORD')
)
app.secret_key = 'hhjsjjfoldjneijfr'
mail = Mail(app)

# SQLite configuration for local server
if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///studentcouncil.db'
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('PROD_URI')

db.init_app(app)


# Club Recruitments Table
class Recruitments(db.Model):
    __tablename__ = 'recruitment'
    roll_no = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    priority1 = db.Column(db.String, nullable=True)
    priority2 = db.Column(db.String, nullable=True)
    priority3 = db.Column(db.String, nullable=True)
    is_shortlisted = db.Column(db.Boolean, default=False)  # New field to track shortlisting


class SCRecruitment(db.Model):
    __tablename__ = 'screcruitment'
    roll_no = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    priority = db.Column(db.String, nullable=True)
    is_shortlisted = db.Column(db.Boolean, default=False)  # New field to track shortlisting


@app.route("/")
def home():
    return render_template('index.html')


@app.route('/admin/export_csv')
def export_csv():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))  # Redirect to login page if not authenticated

    # Create a CSV in memory
    si = StringIO()
    writer = csv.writer(si)

    # Write header for the club recruitments
    writer.writerow(['Roll No', 'Name', 'Phone', 'Email', 'Priority 1', 'Priority 2', 'Priority 3', 'Shortlist Status'])

    # Write club recruitment data
    club_candidates = Recruitments.query.all()
    for candidate in club_candidates:
        writer.writerow([
            candidate.roll_no,
            candidate.name,
            candidate.phone,
            candidate.email,
            candidate.priority1,
            candidate.priority2,
            candidate.priority3,
            'Shortlisted' if candidate.is_shortlisted else 'Not Shortlisted'
        ])

    # Add a blank row to separate club recruitments from student council recruitments
    writer.writerow([])

    # Write header for the student council recruitments
    writer.writerow(['Roll No', 'Name', 'Phone', 'Email', 'Priority', 'Shortlist Status'])

    # Write student council recruitment data
    sc_candidates = SCRecruitment.query.all()
    for candidate in sc_candidates:
        writer.writerow([
            candidate.roll_no,
            candidate.name,
            candidate.phone,
            candidate.email,
            candidate.priority,
            'Shortlisted' if candidate.is_shortlisted else 'Not Shortlisted'
        ])

    # Return the CSV file as a response
    output = si.getvalue()
    si.close()

    # Return as a downloadable response
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=database_export.csv"}
    )


@app.route("/apply-clubs")
def apply():
    return render_template('apply.html')


@app.route("/apply_sc")
def apply_sc():
    return render_template('sc_apply.html')


@app.route("/team")
def team():
    return render_template('team.html')


@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))  # Redirect to login page if not authenticated

    # Get the selected priority from query parameters (for filtering)
    selected_club_priority = request.args.get('club_priority_filter', '')
    selected_sc_priority = request.args.get('sc_priority_filter', '')

    # Get the unique priorities for clubs and student council recruitments
    club_priorities = set([candidate.priority1 for candidate in Recruitments.query.all()] +
                          [candidate.priority2 for candidate in Recruitments.query.all()] +
                          [candidate.priority3 for candidate in Recruitments.query.all()])

    sc_priorities = set([candidate.priority for candidate in SCRecruitment.query.all()])

    # Filter club candidates based on selected priority
    if selected_club_priority:
        club_candidates = Recruitments.query.filter(
            (Recruitments.priority1 == selected_club_priority) |
            (Recruitments.priority2 == selected_club_priority) |
            (Recruitments.priority3 == selected_club_priority)
        ).all()
    else:
        club_candidates = Recruitments.query.all()

    # Filter student council candidates based on selected priority
    if selected_sc_priority:
        sc_candidates = SCRecruitment.query.filter_by(priority=selected_sc_priority).all()
    else:
        sc_candidates = SCRecruitment.query.all()

    return render_template(
        'admin_dashboard.html',
        club_candidates=club_candidates,
        sc_candidates=sc_candidates,
        club_priorities=club_priorities,
        sc_priorities=sc_priorities,
        selected_club_priority=selected_club_priority,
        selected_sc_priority=selected_sc_priority
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin_user = request.form.get("username")
        admin_pass = request.form.get("password")

        if admin_user == params["admin_user"] and admin_pass == params["admin_pass"]:
            session['admin'] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", message="Invalid credentials")
    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for("home"))


@app.route("/apply/submit", methods=["POST"])
def submit():
    data = request.form
    name = request.form.get('name')
    email = request.form.get('email')
    roll_no = request.form.get('roll_no')
    phone = request.form.get('phone')
    priority1 = request.form.get('club_priority_1')
    priority2 = request.form.get('club_priority_2')
    priority3 = request.form.get('club_priority_3')

    # Handle default values for priorities
    if priority1 == "Club Priority 1":
        priority1 = "None"
    if priority2 == "Club Priority 2":
        priority2 = "None"
    if priority3 == "Club Priority 3":
        priority3 = "None"

    # Check if roll_no, email, or phone already exists individually
    existing_entry_roll_no = Recruitments.query.filter_by(roll_no=roll_no).first()
    existing_entry_email = Recruitments.query.filter_by(email=email).first()
    existing_entry_phone = Recruitments.query.filter_by(phone=phone).first()

    # If any constraint is violated, return an appropriate error message
    if existing_entry_roll_no or existing_entry_email or existing_entry_phone:
        return render_template('apply.html',
                               message="Details already exist for either Roll Number, Email, or Phone. Please try again with different details.")

    try:
        # If no duplicate found, insert the new entry
        entry = Recruitments(roll_no=roll_no, name=name, phone=phone, email=email,
                             priority1=priority1, priority2=priority2, priority3=priority3)
        db.session.add(entry)
        db.session.commit()

        return render_template('application_submitted.html', application=data)

    except Exception as e:
        db.session.rollback()  # Rollback in case of an error
        return render_template('apply.html', message=f"An error occurred: {str(e)}")


@app.route('/admin/shortlist/<recruit_type>/<roll_no>', methods=["POST"])
def shortlist_candidate(recruit_type, roll_no):
    if recruit_type == "club":
        candidate = Recruitments.query.filter_by(roll_no=roll_no).first()
    elif recruit_type == "sc":
        candidate = SCRecruitment.query.filter_by(roll_no=roll_no).first()

    if candidate:
        candidate.is_shortlisted = True
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return "Candidate not found", 404


@app.route("/apply-sc/submit_sc", methods=["POST"])
def submit_sc():
    data = request.form
    name = request.form.get('scname')
    email = request.form.get('scemail')
    roll_no = request.form.get('scroll_no')
    phone = request.form.get('scphone')
    priority = request.form.get('verticalpriority')

    # Check if roll_no, email, or phone already exists individually
    existing_entry_roll_no = SCRecruitment.query.filter_by(roll_no=roll_no).first()
    existing_entry_email = SCRecruitment.query.filter_by(email=email).first()
    existing_entry_phone = SCRecruitment.query.filter_by(phone=phone).first()

    # If any of the constraints exist, return a message
    if existing_entry_roll_no or existing_entry_email or existing_entry_phone:
        return render_template('sc_apply.html',
                               message="Details already exist for either Roll Number, Email, or Phone. Please try again with different details.")

    try:
        # If no duplicate found, insert the new entry
        entry = SCRecruitment(roll_no=roll_no, name=name, phone=phone, email=email, priority=priority)
        db.session.add(entry)
        db.session.commit()
        return render_template('application_submitted_sc.html', application=data)

    except Exception as e:
        db.session.rollback()  # Rollback in case of any exception
        return render_template('sc_apply.html', message=f"An error occurred: {str(e)}")


# Flask-Migrate: Create tables before starting the app
with app.app_context():
    db.create_all()

app.run(debug=True)