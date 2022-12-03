import datetime
from sqlite3 import IntegrityError
import sqlite3
from server import db
from server.decorators import login_required
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

EMAIL_SESSION_KEY = 'user_email'

core = Blueprint('core', __name__)
curr_user="none"
user_type="none"
loggedIn = 0

@core.route('/')
def home():
    global user_type
    return render_template('home.html.jinja', user_type=user_type, photographers=photographers)

@core.route('/appt')
def appt():
    photographers = db.User.list_photographers()
    global user_type, curr_user
    is_photographer = False
    appointments = [];
    if 'user' in g:
        user: db.User = g.get('user')
        curr_user = user
        if user and user.type is db.UserType.PHOTOGRAPHER:
            user_type="photographer"
            is_photographer=True
        if user and user.type is db.UserType.CLIENT:
            user_type = "client"
        print(user_type)
        appointments = fetch_appointments(user.email, is_photographer)
    return render_template('appt.html.jinja', is_photographer=is_photographer, user_type=user_type, appointments = appointments, num_appt = len(appointments) , photographers=photographers)

@core.route('/register', methods=('GET', 'POST'))
def register():
    global user_type
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
            db.User.create(email, password, name, phone_number, "none", user_type)
            flash("Thank you for registering")
        except IntegrityError:
            flash(f"Email {email} is already registered")
        return redirect(url_for('.login'))
    
    return render_register_template()

def render_register_template(**context):
    return render_template('register.html.jinja', **context)

@core.route('/login', methods=('GET', 'POST',))
def login():
    global user_type, loggedIn, curr_user
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
            loggedIn = 1
            curr_user=user
            if user and user.type is db.UserType.PHOTOGRAPHER:
                user_type="photographer"
            if user and user.type is db.UserType.CLIENT:
                user_type = "client"
            session[EMAIL_SESSION_KEY] = user.email
            return redirect(url_for('.home'))
        elif err:
            flash(err)
        
    return render_template('login.html.jinja', user_type=user_type)

@core.route('/logout')
def logout():
    global loggedIn, curr_user
    session.clear()
    curr_user="none"
    user_type="none"
    loggedIn = 0;
    return redirect(url_for('.home', user_type=user_type))

@core.route('/photographers/<next>')
def photographers(next: str):
    global user_type
    photographers = db.User.list_photographers()
    return render_template('photographers.html.jinja', user_type=user_type, photographers=photographers, next=next)

@core.route('/gallery/<email>')
def gallery(email: str):
    global curr_user, user_type
    photographer = db.User.read(email)
    albums = db.Album.read(email)
    return render_template('gallery.html.jinja',user_type=user_type, curr_user=curr_user, photographer=photographer, albums=albums)

@login_required
@core.route('/edit_gallery/<email>')
def edit_gallery(email: str):
    global curr_user, user_type
    photographer = db.User.read(email)
    albums = db.Album.read(email)
    return render_template('edit_gallery.html.jinja',user_type=user_type, curr_user=curr_user, photographer=photographer, albums=albums)

@login_required
@core.route("/edit_about/<email>", methods=('POST',)) 
def edit_about(email: str): 
    if request.method == 'POST':
        text = request.form['text']
        db.User.edit_about(text, email)
    return redirect(url_for('core.gallery', user_type=user_type, email=curr_user.email, photographer=curr_user))

@login_required
@core.route("/delete_album/<album_name>", methods=('POST',)) 
def delete_album(album_name: str): 
    global curr_user
    db.Album.delete(curr_user.email, album_name)
    return redirect(url_for('core.gallery', email=curr_user.email))


@login_required
@core.route('/manage', methods=('GET', 'POST'))
def manage():
    global user_type
    user: db.User = g.user
    # for rn, /manage is only for photographers
    if user.type is not db.UserType.PHOTOGRAPHER:
        flash("You don't have sufficient permissions to access this page")
        return redirect(url_for('.home'))
    
    if request.method == 'POST':
        start = request.form['start']
        end = request.form['end']
        db.PhotographerAvailableTime.create(start, end, user.email)
        return redirect(url_for('.manage')) # reload page after post
    
    available_times = db.PhotographerAvailableTime.read_all(user.email, False)
    contact_forms = db.ContactForm.read(user.email)
    return render_template(
        'manage.html.jinja', 
        user=user, 
        user_type=user_type,
        available_times=available_times, 
        contact_forms=contact_forms
    )
    
@login_required
@core.route('/book/<photographer_email>', methods=('GET', 'POST'))
def book(photographer_email: str):
    global user_type
    user: db.User = g.user
    if not user or user.type is not db.UserType.CLIENT:
        flash("You must be a logged in client to book with this photographer")
        return redirect(url_for('.home'))

    if request.method == 'POST':
        err = None
        time_id = int(request.form['time_id'])
        package_id = int(request.form['package_id'])
        confirmed = False

        if not (time_id and package_id):
            err = "All fields must be entered"
        
        if err:
            return render_register_template(error=err)

        db.Appointment.create(time_id, confirmed, package_id, photographer_email, user.email)
        flash("Thank you for your booking!")
        return redirect(url_for('core.gallery', curr_user=curr_user, email=photographer_email))

    
    photographer = db.User.read(photographer_email)
    available_times = db.PhotographerAvailableTime.read_all(photographer_email, False)
    packages = db.Package.read_all(photographer.email)
    packages.sort(key=lambda package: package.pricing)

    return render_template('book.html.jinja', user_type=user_type, photographer=photographer, available_times=available_times, packages=packages)


@login_required
@core.route('/contact/<photographer_email>', methods=('GET', 'POST',))
def contact(photographer_email: str):
    #    flash("You must be a logged in client to contact this photographer")
    #    return redirect(url_for('.home'))
    global loggedIn
    if request.method == 'POST':
        if loggedIn == 1:
            user: db.User = g.user
            name = user.name
            emails = user.email
        elif loggedIn == 0:
            emails = request.form['email']
            name = request.form['name']
            
        message = request.form['message']
        db.ContactForm.create(message, emails, name, photographer_email)
        return redirect(url_for('core.gallery', user_type=user_type, curr_user=curr_user, email=photographer_email))

    photographer = db.User.read(photographer_email)
    return render_template('contact.html.jinja', user_type=user_type, photographer=photographer, loggedIn = loggedIn)

@login_required
@core.route("/confirm_appt/<int:appointment_id>", methods=('POST',)) 
def confirm_appt(appointment_id: int): 
    db.Appointment.confirm(appointment_id)
    return redirect(url_for('core.appt', user_type=user_type, ))

@login_required
@core.route("/delete_appt/<int:appointment_id>", methods=('POST',)) 
def delete_appt(appointment_id: int): 
    db.Appointment.delete(appointment_id)
    return redirect(url_for('core.appt', user_type=user_type))


@login_required
@core.route('/invoice/<int:appointment_id>')
def invoice(appointment_id: int):
    global user_type
    appointment = db.Appointment.read(appointment_id)
    time = db.PhotographerAvailableTime.read(appointment.time_id)
    package = db.Package.read(appointment.package_id)
    photographer = db.User.read(appointment.photographer_email)
    client = db.User.read(appointment.client_email)

    invoice = db.Invoice.create(datetime.datetime.now(), package.pricing, package.items, appointment.id)
    return render_template('invoice.html.jinja', user_type=user_type, appointment=appointment, invoice=invoice, time=time, client=client, photographer=photographer)

# TODO: this should be a `DELETE` method, written as POST to save time for project
@core.route("/available-time/delete/<int:id>", methods=('POST',))
def delete_available_time(id: int):
    db.PhotographerAvailableTime.delete(id)
    return redirect(url_for('.manage'))

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
