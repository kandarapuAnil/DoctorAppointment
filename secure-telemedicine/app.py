from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired
from pymongo import MongoClient
from bson import ObjectId
import datetime
from flask import jsonify

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# MongoDB Setup
client = MongoClient("mongodb://localhost:27017/")
db = client['doctor_patient_db']
users = db['users']
appointments = db['appointments']
feedbacks = db['feedback']
prescriptions = db['prescriptions']
contact_messages = db['contact_messages']

# Forms
class RegisterForm(FlaskForm):
    role = SelectField('Role', choices=[('doctor', 'Doctor'), ('patient', 'Patient')])
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    role = SelectField('Role', choices=[('doctor', 'Doctor'), ('patient', 'Patient')])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

    

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        users.insert_one({
            "role": form.role.data,
            "name": form.name.data,
            "email": form.email.data,
            "password": form.password.data
        })
        flash("Registered successfully! Please log in.")
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = users.find_one({"email": form.email.data, "password": form.password.data, "role": form.role.data})
        if user:
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            if user['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash("Invalid credentials.")
    return render_template('login.html', form=form)

@app.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if session.get('role') != 'doctor':
        return redirect('/')
    doctor_id = session.get('user_id')
    doctor_data = users.find_one({"_id": ObjectId(doctor_id)})

    if request.method == 'POST':
        users.update_one({"_id": ObjectId(doctor_id)}, {"$set": {
            "specialization": request.form['specialization'],
            "experience": request.form['experience'],
            "council_id": request.form['council_id'],
            "availability": request.form['availability'],
            "fee_hour": request.form['fee_hour'],
            "fee_day": request.form['fee_day'],
            "fee_month": request.form['fee_month'],
            "video_link": request.form['video_link'],
            "address": request.form['address'],
            "contact": request.form['contact']
        }})
        flash("Profile updated.")
        return redirect(url_for('doctor_dashboard'))

    posted_prescriptions = prescriptions.find({"doctor_id": doctor_id})
    patient_appointments = appointments.find({"doctor_id": doctor_id})

    return render_template('doctor_dashboard.html', doctor=doctor_data, posted_prescriptions=posted_prescriptions, appointments=patient_appointments)

@app.route('/doctor/post_prescription', methods=['POST'])
def post_prescription():
    if session.get('role') != 'doctor':
        return redirect('/')
    prescriptions.insert_one({
        "doctor_id": session['user_id'],
        "patient_email": request.form['patient_email'],
        "disease": request.form['disease'],
        "prescription": request.form['prescription']
    })
    flash("Prescription posted.")
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/edit_prescription/<pres_id>', methods=['GET', 'POST'])
def edit_prescription(pres_id):
    prescription = prescriptions.find_one({"_id": ObjectId(pres_id)})
    if request.method == 'POST':
        prescriptions.update_one({"_id": ObjectId(pres_id)}, {"$set": {
            "disease": request.form['disease'],
            "prescription": request.form['prescription']
        }})
        flash("Prescription updated.")
        return redirect(url_for('doctor_dashboard'))
    return render_template('edit_prescription.html', prescription=prescription)

@app.route('/doctor/delete_prescription/<pres_id>', methods=['POST'])
def delete_prescription(pres_id):
    prescriptions.delete_one({"_id": ObjectId(pres_id)})
    flash("Prescription deleted.")
    return redirect(url_for('doctor_dashboard'))

@app.route('/patient_dashboard')
def patient_dashboard():
    if session.get('role') != 'patient':
        return redirect('/')
    all_doctors = users.find({"role": "doctor"})
    patient_email = users.find_one({"_id": ObjectId(session['user_id'])})['email']
    my_prescriptions = prescriptions.find({"patient_email": patient_email})
    return render_template('patient_dashboard.html', doctors=all_doctors, prescriptions=my_prescriptions)

@app.route('/doctor/<doctor_id>')
def doctor_details(doctor_id):
    doctor = users.find_one({"_id": ObjectId(doctor_id)})
    return render_template('doctor_details.html', doctor=doctor)

@app.route('/book/<doctor_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id):
    if session.get('role') != 'patient':
        return redirect('/')
    if request.method == 'POST':
        appointments.insert_one({
            "doctor_id": doctor_id,
            "patient_id": session['user_id'],
            "patient_name": users.find_one({"_id": ObjectId(session['user_id'])})['name'],
            "date_time": request.form['date_time'],
            "message": request.form['message']
        })
        flash("Appointment booked!")
        return redirect(url_for('patient_dashboard'))
    return render_template('appointment_booking.html', doctor_id=doctor_id)

@app.route('/feedback/<doctor_id>', methods=['POST'])
def leave_feedback(doctor_id):
    rating = request.form['rating']
    comment = request.form['comment']
    feedbacks.insert_one({
        "doctor_id": doctor_id,
        "patient_id": session['user_id'],
        "rating": rating,
        "comment": comment,
        "created_at": datetime.datetime.utcnow()
    })
    flash("Thanks for your feedback!")
    return redirect(url_for('doctor_details', doctor_id=doctor_id))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')

    if name and email and message:
        contact_messages.insert_one({
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "created_at": datetime.datetime.utcnow()
        })
        flash("Message submitted successfully!")
    else:
        flash("Please fill in all required fields.")

    return redirect(url_for('contact'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)
