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
