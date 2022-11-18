-- TODO: add sql schema statements to here
DROP TABLE IF EXISTS feedback_form;
DROP TABLE IF EXISTS form;
DROP TABLE IF EXISTS invoice;
DROP TABLE IF EXISTS appointment;
DROP TABLE IF EXISTS package;
DROP TABLE IF EXISTS photo;
DROP TABLE IF EXISTS album;
DROP TABLE IF EXISTS photographer_available_time;
DROP TABLE IF EXISTS user_type;
DROP TABLE IF EXISTS user;

CREATE TABLE user_type (
    user_type TEXT PRIMARY KEY NOT NULL
);

INSERT INTO user_type (user_type) VALUES ('photographer');
INSERT INTO user_type (user_type) VALUES ('client');
-- NOTE: frozen table do not modify

CREATE TABLE user (
    email TEXT PRIMARY KEY NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    type TEXT NOT NULL REFERENCES user_type (user_type) ON DELETE CASCADE
);

CREATE TABLE photographer_available_time (
    id INTEGER PRIMARY KEY NOT NULL,
    -- following are datetimes
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    photographer_email TEXT NOT NULL REFERENCES user (email) ON DELETE CASCADE
);

CREATE TABLE album (
    name TEXT PRIMARY KEY NOT NULL,
    type TEXT NOT NULL,
    release_type TEXT NOT NULL,
    photographer_email TEXT NOT NULL REFERENCES user (email) ON DELETE CASCADE
 );

 CREATE TABLE photo (
    id INTEGER PRIMARY KEY NOT NULL,
    pathname TEXT NOT NULL,
    album_name TEXT NOT NULL REFERENCES album (name) ON DELETE CASCADE
 );

CREATE TABLE package (
    id INTEGER PRIMARY KEY NOT NULL,
    pricing INTEGER NOT NULL,
    items TEXT NOT NULL,
    photographer_email TEXT NOT NULL REFERENCES user (email) ON DELETE CASCADE
);

CREATE TABLE appointment (
    id INTEGER PRIMARY KEY NOT NULL,
    time_id INTEGER NOT NULL REFERENCES photographer_available_time (id) ON DELETE CASCADE,
    package_id INTEGER NOT NULL REFERENCES package (id) ON DELETE CASCADE,
    photographer_email TEXT NOT NULL REFERENCES user (email) ON DELETE CASCADE,
    client_email TEXT NOT NULL REFERENCES user (email) ON DELETE CASCADE
);

CREATE TABLE invoice (
    id INTEGER PRIMARY KEY NOT NULL,
    date TEXT NOT NULL,
    total_cost INTEGER NOT NULL,
    cost TEXT NOT NULL,
    appointment_id INTEGER UNIQUE NOT NULL REFERENCES appointment (id) ON DELETE CASCADE
);

CREATE TABLE form (
    id INTEGER PRIMARY KEY NOT NULL,
    message TEXT NOT NULL,
    client_email TEXT NOT NULL REFERENCES user (email) ON DELETE CASCADE,
    photographer_email TEXT NOT NULL REFERENCES user (email) ON DELETE CASCADE
);

CREATE TABLE feedback_form (
    id INTEGER PRIMARY KEY NOT NULL,
    form_id INTEGER NOT NULL REFERENCES form (id) ON DELETE CASCADE,
    invoice_id INTEGER NOT NULL REFERENCES invoice (id) ON DELETE CASCADE
);
