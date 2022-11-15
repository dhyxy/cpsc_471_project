import datetime
from sqlite3 import IntegrityError
from server import db
from server.decorators import login_required
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

EMAIL_SESSION_KEY = 'user_email'

core = Blueprint('core', __name__)

@core.route('/')
def home():
    photographers = db.User.list_photographers()
    user: db.User = g.get('user')
    return render_template('home.html.jinja', photographers=photographers, is_photographer=user and user.type is db.UserType.PHOTOGRAPHER)

@core.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        err = None

        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        phone_number = request.form['phone_number']
        try:
            user_type = db.UserType.from_string(request.form['user_type'])
        except ValueError as e:
            err = str(e)

        if not (email and password and name and phone_number):
            err = "All fields must be entered"
        
        if err:
            return render_register_template(error=err)

        try:
            # TODO(1): for the project we aren't hashing the password for simplicity
            # if you end up deploying this, hash the passwords on registration
            # and check password on login with hash
            db.User.create(email, password, name, phone_number, user_type.value) # type: ignore 
            flash("Thank you for registering")
        except IntegrityError:
            flash(f"Email {email} is already registered")
        return redirect(url_for('.login'))
    
    return render_register_template()

def render_register_template(**context):
    return render_template('register.html.jinja', USER_TYPES=db.USER_TYPE_VALUES, **context)

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

@core.route('/photographers/<email>')
def photographer(email: str):
    photographer_ = db.User.read(email)
    albums = db.Album.read(email)
    return render_template('photographer.html.jinja', photographer=photographer_, albums=albums)

@login_required
@core.route('/profile', methods=('GET', 'POST'))
def profile():
    user: db.User = g.user
    # for rn, /profile is only for photographers
    if user.type is not db.UserType.PHOTOGRAPHER:
        flash("You don't have sufficient permissions to access this page")
        return redirect(url_for('.home'))

    available_times = db.PhotographerAvailableTime.read(user.email)

    if request.method == 'POST':
        start = request.form['start']
        end = request.form['end']
        db.PhotographerAvailableTime.create(start, end, user.email)
        return redirect(url_for('.profile')) # reload page after post
    
    return render_template('profile.html.jinja', user=user, available_times=available_times)

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

