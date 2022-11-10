from sqlite3 import IntegrityError
from server import db
from flask import Blueprint, flash, redirect, render_template, request, url_for

core = Blueprint('core', __name__)

@core.route('/')
def home():
    return render_template('home.html.jinja')

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
        pass
    return render_template('login.html.jinja')