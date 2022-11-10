from server.db import get_db
from flask import Blueprint, render_template

core = Blueprint('core', __name__)

@core.route('/')
def home():
    return render_template('home.html.jinja')