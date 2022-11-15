from __future__ import annotations
import datetime

import sqlite3
from dataclasses import dataclass, field
from enum import Enum

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
    cursor.execute("INSERT INTO user(email, password, name, phone_number, type) VALUES ('photo@email.com', 'password', 'photo1', '123', 'photographer');")
    cursor.execute("INSERT INTO album(name, type, release_type, photographer_email) VALUES ('alb1', 'photos', 'idk', 'photo@email.com');")
    cursor.execute("INSERT INTO photo(pathname, album_name) VALUES ('/test/img.png', 'alb1');")
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
    READ = "SELECT * FROM photographer_available_time WHERE photographer_email = ?"
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
    def read(photographer_email: str) -> list[PhotographerAvailableTime]:
        db = get_db()
        data = db.execute(PhotographerAvailableTime.READ, (photographer_email,))
        available_times = [PhotographerAvailableTime(**row) for row in data]
        return available_times
    
    @staticmethod
    @tries_to_commit
    def delete(id: int) -> None:
        db = get_db()
        db.execute(PhotographerAvailableTime.DELETE, (id,))
        db.commit()

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
