from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from celery import Celery
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///application.db'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
Bootstrap(app)
db = SQLAlchemy(app)

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

class University(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(50))

class Professor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'))

class Deadline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    type = db.Column(db.String(50))
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'))

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'))

class EmailTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)

def send_email(to_email, subject, body):
    sender = "mohammadhanifahmadi36.com"  # ایمیل خودتون
    password = "mvvg yjes ailo blil"   # رمز اپلیکیشن Gmail
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        server.send_message(msg)

@celery.task
def schedule_email(to_email, subject, body, send_time):
    now = datetime.now()
    if now >= send_time:
        send_email(to_email, subject, body)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'university_name' in request.form:
            university = University(name=request.form['university_name'], country=request.form['country'])
            db.session.add(university)
            db.session.commit()
        elif 'professor_name' in request.form:
            professor = Professor(name=request.form['professor_name'], email=request.form['professor_email'], university_id=request.form['university_id'])
            db.session.add(professor)
            db.session.commit()
        elif 'deadline_date' in request.form:
            deadline = Deadline(date=datetime.strptime(request.form['deadline_date'], '%Y-%m-%d'), type=request.form['deadline_type'], university_id=request.form['university_id'])
            db.session.add(deadline)
            db.session.commit()
        elif 'document_type' in request.form:
            document = Document(type=request.form['document_type'], university_id=request.form['university_id'])
            db.session.add(document)
            db.session.commit()
    universities = University.query.all()
    professors = Professor.query.all()
    deadlines = Deadline.query.all()
    documents = Document.query.all()
    return render_template('index.html', universities=universities, professors=professors, deadlines=deadlines, documents=documents)

@app.route('/templates', methods=['GET', 'POST'])
def email_templates():
    if request.method == 'POST':
        if 'template_name' in request.form:
            template = EmailTemplate(name=request.form['template_name'], content=request.form['template_content'])
            db.session.add(template)
            db.session.commit()
        elif 'send_email' in request.form:
            template = EmailTemplate.query.get(request.form['template_id'])
            to_email = request.form['to_email']
            subject = "Application Email"
            body = template.content.format(name="User", university="Example University")
            send_time = datetime.strptime(request.form['send_time'], '%Y-%m-%dT%H:%M')
            schedule_email.apply_async(args=[to_email, subject, body, send_time], eta=send_time)
    templates = EmailTemplate.query.all()
    return render_template('email_templates.html', templates=templates)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)