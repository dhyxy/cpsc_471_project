import datetime
from sqlite3 import IntegrityError
import sqlite3
from server import db
from server.decorators import login_required
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

EMAIL_SESSION_KEY = 'user_email'

core = Blueprint('core', __name__)
user_type="none"

@core.route('/')
def home():
    global user_type
    if 'user' in g:
        user: db.User = g.get('user')
        if user and user.type is db.UserType.PHOTOGRAPHER:
            user_type="photographer"
        if user and user.type is db.UserType.CLIENT:
            user_type = "client"
        print(user_type)
    return render_template('home.html.jinja', user_type=user_type, photographers=photographers)

@core.route('/appt')
def appt():
    photographers = db.User.list_photographers()
    is_photographer = False
    appointments = [];
    if 'user' in g:
        user: db.User = g.get('user')
        is_photographer = user and user.type is db.UserType.PHOTOGRAPHER
        appointments = fetch_appointments(user.email, is_photographer)
    return render_template('home.html.jinja', user_type=user_type, appointments = appointments)

@core.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        err = None

        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        phone_number = request.form['phone_number']
        user_type =  db.UserType.CLIENT
        
        if not (email and password and name and phone_number):
            err = "All fields must be entered"
        
        if err:
            return render_register_template(error=err)

        try:
            # TODO(1): for the project we aren't hashing the password for simplicity
            # if you end up deploying this, hash the passwords on registration
            # and check password on login with hash
            db.User.create(email, password, name, phone_number, user_type)
            flash("Thank you for registering")
        except IntegrityError:
            flash(f"Email {email} is already registered")
        return redirect(url_for('.login'))
    
    return render_register_template()

def render_register_template(**context):
    return render_template('register.html.jinja', **context)

@core.route('/login', methods=('GET', 'POST',))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = None
        err = None
        try:
            user = db.User.read(email)
        except ValueError as e:
            err = str(e)
        
        # TODO(1): same as first comment, this should be comparing password
        if user and user.password != password:
            err = "Incorrect password"
        
        if user and not err:
            session.clear()
            session[EMAIL_SESSION_KEY] = user.email
            return redirect(url_for('.home'))
        elif err:
            flash(err)
        
    return render_template('login.html.jinja')

@core.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('.home'))

@core.route('/photographers/<next>')
def photographers(next: str):
    photographers = db.User.list_photographers()
    return render_template('photographers.html.jinja', user_type=user_type, photographers=photographers, next=next)

@core.route('/gallery/<email>')
def gallery(email: str):
    photographer_ = db.User.read(email)
    albums = db.Album.read(email)
    print(user_type)
    return render_template('gallery.html.jinja',user_type=user_type, photographer=photographer_, albums=albums)

@login_required
@core.route('/profile', methods=('GET', 'POST'))
def profile():
    global user_type
    user: db.User = g.user
    # for rn, /profile is only for photographers
    if user.type is not db.UserType.PHOTOGRAPHER:
        flash("You don't have sufficient permissions to access this page")
        return redirect(url_for('.home'))
    
    if request.method == 'POST':
        start = request.form['start']
        end = request.form['end']
        db.PhotographerAvailableTime.create(start, end, user.email)
        return redirect(url_for('.profile')) # reload page after post
    
    available_times = db.PhotographerAvailableTime.read_all(user.email)
    contact_forms = db.ContactForm.read(user.email)
    return render_template(
        'profile.html.jinja', 
        user=user, 
        user_type=user_type,
        available_times=available_times, 
        contact_forms=contact_forms
    )
    
@login_required
@core.route('/book/<photographer_email>', methods=('GET', 'POST'))

def book(photographer_email: str):
    user: db.User = g.user
    if not user or user.type is not db.UserType.CLIENT:
        flash("You must be a logged in client to book with this photographer")
        return redirect(url_for('.home'))

    if request.method == 'POST':
        time_id = int(request.form['time_id'])
        package_id = int(request.form['package_id'])
        db.Appointment.create(time_id, package_id, photographer_email, user.email)
        return redirect(url_for('.photographer', email=photographer_email))
    
    photographer = db.User.read(photographer_email)
    available_times = db.PhotographerAvailableTime.read_all(photographer_email, False)
    packages = db.Package.read_all(photographer.email)
    packages.sort(key=lambda package: package.pricing)

    return render_template('book.html.jinja', user_type=user_type, photographer=photographer, available_times=available_times, packages=packages)

@login_required
@core.route('/contact/<photographer_email>', methods=('GET', 'POST',))
def contact(photographer_email: str):
    user: db.User = g.user
    if not user or user.type is not db.UserType.CLIENT:
        flash("You must be a logged in client to contact this photographer")
        return redirect(url_for('.home'))

    if request.method == 'POST':
        message = request.form['message']
        db.ContactForm.create(message, user.email, photographer_email)
        return redirect(url_for('core.gallery', email=photographer_email))

    photographer = db.User.read(photographer_email)
    return render_template('contact.html.jinja', user_type=user_type, photographer=photographer)

@login_required
@core.route('/invoice/<int:appointment_id>')
def invoice(appointment_id: int):
    appointment = db.Appointment.read(appointment_id)
    time = db.PhotographerAvailableTime.read(appointment.time_id)
    package = db.Package.read(appointment.package_id)
    photographer = db.User.read(appointment.photographer_email)

    invoice = db.Invoice.create(datetime.datetime.now(), package.pricing, package.items, appointment.id)
    return render_template('invoice.html.jinja', user_type=user_type, invoice=invoice, time=time, photographer=photographer)

# TODO: this should be a `DELETE` method, written as POST to save time for project
@core.route("/available-time/delete/<int:id>", methods=('POST',))
def delete_available_time(id: int):
    db.PhotographerAvailableTime.delete(id)
    return redirect(url_for('.profile'))

@core.before_app_request
def load_user():
    user_email = session.get(EMAIL_SESSION_KEY)

    if user_email:
        g.user = db.User.read(user_email)

@core.context_processor
def inject_constants():
    return dict(EMAIL_SESSION_KEY=EMAIL_SESSION_KEY)

def fetch_appointments(email: str, is_photographer: bool):
    db_ = db.get_db()
    data = db_.execute(
        f"SELECT * FROM appointment a LEFT JOIN photographer_available_time pat ON a.time_id = pat.id LEFT JOIN package p ON a.package_id = p.id WHERE a.{'photographer_email' if is_photographer else 'client_email'} = ?", 
        (email,)
    ).fetchall()
    return [_parse_times(row) for row in data]

def _parse_times(appointment: sqlite3.Row):
    parsed_appointment = dict(appointment)
    parsed_appointment['start_time'] = datetime.datetime.fromisoformat(appointment['start_time'])
    parsed_appointment['end_time'] = datetime.datetime.fromisoformat(appointment['end_time'])
    return parsed_appointment
