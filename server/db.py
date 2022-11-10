from dataclasses import dataclass
from enum import Enum
import sqlite3

import click
from flask import Flask, current_app, g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()

    cursor = db.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('db init-ed 🤪')

def init_app(app: Flask):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


class UserType(Enum):
    PHOTOGRAPHER = 'photographer'
    CLIENT = 'client'

    @staticmethod
    def from_string(string: str):
        for val in UserType:
            if val.value == string:
                return val
        raise ValueError(f"{string} not included in {__class__}")

USER_TYPE_VALUES = [val.value for val in UserType]

@dataclass
class User:
    email: str
    password: str
    name: str
    phone_number: str
    user_type: UserType

    CREATE = "INSERT INTO user (email, password, name, phone_number, type) VALUES (?, ?, ?, ?, ?)"

    @staticmethod
    def create(email: str, password: str, name: str, phone_number: str, user_type: UserType):
        db = get_db()
        db.execute(User.CREATE, (email, password, name, phone_number, user_type))
        db.commit()