DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS user_type;

CREATE TABLE user_type (
    type TEXT PRIMARY KEY NOT NULL
);

INSERT INTO user_type(type) VALUES ('photographer');
INSERT INTO user_type(type) VALUES ('client');
-- NOTE: frozen table do not modify

CREATE TABLE user (
    email TEXT PRIMARY KEY NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    type TEXT NOT NULL REFERENCES user_type(type) on UPDATE CASCADE
);

