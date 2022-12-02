from __future__ import annotations
import datetime

import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import click
from flask import Flask, current_app, g

from server.decorators import tries_to_commit


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
    db.commit()

    with current_app.open_resource('schema.sql') as f:
        script = f.read().decode('utf8')
        try:
            db.executescript(script)
        except sqlite3.IntegrityError as e:
            click.echo(e)
    
    cursor = db.cursor()
    cursor.execute("INSERT INTO user(email, password, name, phone_number, type) VALUES ('photo@email.com', 'password', 'Anna', '123', 'photographer');")
    cursor.execute("INSERT INTO user(email, password, name, phone_number, type) VALUES ('photo2@email.com', 'password', 'Kyle', '234', 'photographer');")
    cursor.execute("INSERT INTO user(email, password, name, phone_number, type) VALUES ('photo3@email.com', 'password', 'Jane', '234', 'photographer');")
    cursor.execute("INSERT INTO album(name, type, release_type, photographer_email) VALUES ('alb1', 'photos', 'idk', 'photo@email.com');")
    cursor.execute("INSERT INTO photo(pathname, album_name) VALUES ('/test/img.png', 'alb1');")
    cursor.execute("INSERT INTO package(pricing, items, photographer_email) VALUES (120, '1,2,3', 'photo@email.com'), (50, '4', 'photo@email.com');")
    cursor.execute("INSERT INTO user(email, password, name, phone_number, type) VALUES ('client@email.com', 'password', 'client', '123', 'client');")
    cursor.close()
    db.commit()

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
    type: UserType

    CREATE = "INSERT INTO user (email, password, name, phone_number, type) VALUES (?, ?, ?, ?, ?)"
    READ = "SELECT * FROM user WHERE email = ?"

    LIST_PHOTOGRAPHERS = "SELECT * FROM user WHERE type = 'photographer'"

    def __post_init__(self):
        if not isinstance(self.type, UserType):
            self.type = UserType.from_string(str(self.type))

    @staticmethod
    @tries_to_commit
    def create(email: str, password: str, name: str, phone_number: str, type: UserType) -> User:
        db = get_db()
        db.execute(User.CREATE, (email, password, name, phone_number, type.value))
        db.commit()
        return User(email, password, name, phone_number, type)

    @staticmethod 
    def read(email: str) -> User:
        db = get_db()
        data = db.execute(User.READ, (email,)).fetchone()
        if not data:
            raise ValueError(f"no user exists with email: {email}")
        user = User(**data)
        return user

    @staticmethod
    def list_photographers() -> list[User]:
        db = get_db()
        data = db.execute(User.LIST_PHOTOGRAPHERS).fetchall()
        print("data: " + str(data))
        photographers = [User(**row) for row in data]
        return photographers

@dataclass
class PhotographerAvailableTime:
    id: int
    # these are stored as text in SQLite, parsed to datetime in __post_init__
    start_time: str
    end_time: str
    photographer_email: str

    start_parsed: datetime.datetime = field(init=False)
    end_parsed: datetime.datetime = field(init=False)

    CREATE = "INSERT INTO photographer_available_time (start_time, end_time, photographer_email) VALUES (?, ?, ?)"
    READ = "SELECT * FROM photographer_available_time where id = ?"
    READ_ALL = "SELECT * FROM photographer_available_time WHERE photographer_email = ?"
    READ_AVAILABLE = "SELECT * FROM photographer_available_time WHERE id NOT IN (SELECT time_id FROM appointment) AND photographer_email = ?"
    DELETE = "DELETE FROM photographer_available_time WHERE id = ?"

    def __post_init__(self):
        self.start_parsed = datetime.datetime.fromisoformat(self.start_time)
        self.end_parsed = datetime.datetime.fromisoformat(self.end_time)
    
    @staticmethod
    @tries_to_commit
    def create(start_time: str, end_time: str, photographer_email: str) -> PhotographerAvailableTime:
        db = get_db()
        c = db.execute(PhotographerAvailableTime.CREATE, (start_time, end_time, photographer_email))
        db.commit()
        assert c.lastrowid is not None # TODO: this is unstable, fix if app is deployed
        return PhotographerAvailableTime(c.lastrowid, start_time, end_time, photographer_email)
    
    @staticmethod
    def read_all(photographer_email: str, include_booked = True) -> list[PhotographerAvailableTime]:
        db = get_db()
        data = db.execute(
            PhotographerAvailableTime.READ_ALL if include_booked else PhotographerAvailableTime.READ_AVAILABLE,
            (photographer_email,)
        )
        available_times = [PhotographerAvailableTime(**row) for row in data]
        return available_times
    
    @staticmethod
    def read(id: int) -> PhotographerAvailableTime:
        db = get_db()
        data = db.execute(PhotographerAvailableTime.READ, (id,)).fetchone()
        return PhotographerAvailableTime(**data)
    
    @staticmethod
    @tries_to_commit
    def delete(id: int) -> None:
        db = get_db()
        db.execute(PhotographerAvailableTime.DELETE, (id,))
        db.commit()

@dataclass
class Package:
    id: int
    pricing: int
    items: str
    photographer_email: str

    READ_ALL = "SELECT * FROM package WHERE photographer_email = ?"
    READ = "SELECT * FROM package WHERE id = ?"

    @staticmethod
    def read_all(photographer_email: str) -> list[Package]:
        db = get_db()
        data = db.execute(Package.READ_ALL, (photographer_email,))
        packages = [Package(**row) for row in data]
        return packages

    @staticmethod
    def read(id: int) -> Package:
        db = get_db()
        data = db.execute(Package.READ, (id,)).fetchone()
        return Package(**data)

@dataclass
class Appointment:
    id: int
    confirmed: bool
    time_id: int
    package_id: int
    photographer_email: str
    client_email: str

    CREATE = "INSERT INTO appointment (time_id, confirmed, package_id, photographer_email, client_email) VALUES (?, ?, ?, ?, ?)"
    READ_CLIENT = "SELECT * FROM appointment WHERE client_email = ?"
    READ_PHOTOGRAPHER = "SELECT * FROM appointment WHERE photographer_email = ?"
    CONFIRM = "UPDATE appointment SET confirmed = True WHERE id = ?"
    READ = "SELECT * FROM appointment WHERE id = ?"
    DELETE = "DELETE FROM appointment WHERE id = ?"

    @staticmethod
    @tries_to_commit
    def create(time_id: int, confirmed: bool, package_id: int, photographer_email: str, client_email: str) -> Appointment:
        db = get_db()
        c = db.execute(Appointment.CREATE, (time_id, confirmed, package_id, photographer_email, client_email))
        db.commit()
        assert c.lastrowid is not None # TODO unstable, fix if deployed
        return Appointment(c.lastrowid, time_id, confirmed, package_id, photographer_email, client_email)

    @staticmethod
    def read_all(email: str, is_client = True) -> list[Appointment]:
        db = get_db()
        data = db.execute(Appointment.READ_CLIENT if is_client else Appointment.READ_PHOTOGRAPHER, (email,)).fetchall()
        appointments = [Appointment(**row) for row in data]
        return appointments
    
    @staticmethod
    def read(appointment_id: int) -> Appointment:
        db = get_db()
        data = db.execute(Appointment.READ, (appointment_id,)).fetchone()
        return Appointment(**data)

    @staticmethod
    def confirm(appointment_id: int) -> Appointment:
        db = get_db()
        db.execute(Appointment.CONFIRM, (appointment_id,))
        db.commit()

    @staticmethod
    def delete(appointment_id: int) -> Appointment:
        db = get_db()
        db.execute(Appointment.DELETE, (appointment_id,))
        db.commit()

@dataclass
class Invoice:
    id: int
    date: str
    total_cost: int
    cost: str
    appointment_id: int

    parsed_date: datetime.datetime = field(init=False)

    CREATE = "INSERT INTO invoice (date, total_cost, cost, appointment_id) VALUES (?, ?, ?, ?)"
    READ = "SELECT * FROM invoice WHERE appointment_id = ?"

    def __post_init__(self):
        self.parsed_date = datetime.datetime.fromisoformat(self.date)

    @staticmethod
    @tries_to_commit
    def create(date: datetime.datetime, total_cost: int, cost: str, appointment_id: int) -> Invoice:
        invoice = Invoice.read(appointment_id)
        if invoice:
            return invoice
        db = get_db()
        date_str = date.isoformat()
        c = db.execute(Invoice.CREATE, (date_str, total_cost, cost, appointment_id))
        db.commit()
        assert c.lastrowid is not None # TODO: unstable
        return Invoice(c.lastrowid, date_str, total_cost, cost, appointment_id)
    
    @staticmethod
    def read(appointment_id: int) -> Optional[Invoice]:
        db = get_db()
        data = db.execute(Invoice.READ, (appointment_id,)).fetchone()
        return None if not data else Invoice(**data)

@dataclass
class Album:
    name: str
    type: str
    release_type: str
    photographer_email: str

    photos: list[Photo] = field(default_factory=list, init=False)

    READ = "SELECT a.* FROM album a LEFT JOIN user ON a.photographer_email = user.email WHERE a.photographer_email = ?"

    def __post_init__(self):
        # TODO: inefficient, should probably condense into a join
        self.photos = Photo.read(self.name)

    @staticmethod
    def read(photographer_email: str) -> list[Album]:
        db = get_db()
        data = db.execute(Album.READ, (photographer_email,)).fetchall()
        albums = [Album(**row) for row in data]
        return albums

@dataclass
class Photo:
    id: int
    pathname: str
    album_name: str
    
    READ = "SELECT * FROM photo WHERE album_name = ?"

    @staticmethod
    def read(album_name: str) -> list[Photo]:
        db = get_db()
        data = db.execute(Photo.READ, (album_name,)).fetchall()
        photos = [Photo(**row) for row in data]
        return photos

@dataclass
class ContactForm:
    id: int
    client_name: str
    message: str
    client_email: str
    photographer_email: str

    CREATE = "INSERT INTO form (message, client_email, client_name, photographer_email) VALUES (?, ?, ?, ?)"
    READ = "SELECT * FROM form WHERE photographer_email = ?"

    @staticmethod
    @tries_to_commit
    def create(message: str, client_email: str, client_name:str, photographer_email: str) -> ContactForm:
        db = get_db()
        c = db.execute(ContactForm.CREATE, (message, client_email, client_name, photographer_email))
        db.commit()
        assert c.lastrowid is not None # TODO unstable
        return ContactForm(c.lastrowid, message, client_email, client_name, photographer_email)

    @staticmethod
    def read(photographer_email: str) -> list[ContactForm]:
        db = get_db()
        data = db.execute(ContactForm.READ, (photographer_email,))
        forms = [ContactForm(**row) for row in data]
        return forms