import flask
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
import json
from dotenv import load_dotenv
import os


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
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=os.getenv('GMAIL_PASSWORD')
)
mail = Mail(app)
if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('LOCAL_URI')
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('PROD_URI')

db.init_app(app)


class Recruitments(db.Model):
    __tablename__ = 'recruitment'
    roll_no: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=False, nullable=False)
    phone: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    priority1: Mapped[str] = mapped_column(unique=False, nullable=True)
    priority2: Mapped[str] = mapped_column(unique=False, nullable=True)
    priority3: Mapped[str] = mapped_column(unique=False, nullable=True)


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/apply")
def apply():
    return render_template('apply.html')


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

    if priority1 == "Club Priority 1":
        priority1 = "None"
    if priority2 == "Club Priority 2":
        priority2 = "None"
    if priority3 == "Club Priority 3":
        priority3 = "None"

    existing_entry = Recruitments.query.filter_by(roll_no=roll_no).first()
    existing_entry_mail = Recruitments.query.filter_by(email=email).first()
    existing_entry_phone = Recruitments.query.filter_by(phone=phone).first()
    existing_entry = existing_entry and existing_entry_phone
    existing_entry = existing_entry and existing_entry_mail
    if existing_entry:
        return render_template('apply.html',
                               message="Details already exist. Please try again with a different one.")
    else:
        entry = Recruitments(roll_no=roll_no, name=name, phone=phone, email=email,
                             priority1=priority1, priority2=priority2, priority3=priority3)
        db.session.add(entry)
        db.session.commit()

        if email and '@' in email:
            mail.send_message('Congratulations ' + name + '! We have Received your application!',
                              sender=params['gmail-user'],
                              recipients=[email],
                              body="We have received your application with the following details. Please visit the "
                                   "website"
                                   "for auditions/interview dates and venue.\nAll The Best!\n\n\n"
                                   "Name: " + name + "\nEmail ID: " + email + "\nRoll Number: " + roll_no + "\nPhone "
                                                                                                            "Number:"
                                   + phone + "\nClub Priority 1: " + priority1 + "\nClub Priority 2: " + priority2 +
                                   "\nClub Priority 3: " + priority3 + "\n\n\nStudent Council\nJECRC")
        else:
            print("Invalid email address")

        return render_template('application_submitted.html', application=data)


app.run(debug=True)
