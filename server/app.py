from server.db import get_db
from flask import Blueprint, render_template

core = Blueprint('core', __name__)

@core.route('/')
def home():
    return render_template('home.html.jinja')

@core.route('/photographers')
def photographers():

    # this is static data, but this will be fetched from the database in the actual app
    # probably will be the easiest way to prototype new pages
    photographers = [{'name': 'asdlkfj', 'email': 'email@email.com'}, {'name': 'namey name', 'email': 'emaily@email.com'}]
    return render_template('photographers.html.jinja', photographers=photographers)