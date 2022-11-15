from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import sqlite3
from typing import Optional

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
        self.type = UserType.from_string(str(self.type))

    @staticmethod
    def create(email: str, password: str, name: str, phone_number: str, type: UserType) -> Optional[User]:
        db = get_db()
        try:
            db.execute(User.CREATE, (email, password, name, phone_number, type))
            db.commit()
            return User(email, password, name, phone_number, type)
        except sqlite3.Error as e:
            current_app.logger.error(e)
        return None

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
class Album:
    name: str
    type: str
    release_type: str
    photographer_email: str

    photos: list[Photo] = field(default_factory=list, init=False)

    READ = "SELECT a.* FROM album a LEFT JOIN user ON a.photographer_email = user.email WHERE a.photographer_email = ?"

    def __post_init__(self):
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
