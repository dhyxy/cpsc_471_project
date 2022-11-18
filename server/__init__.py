import os

from flask import Flask

from server import db


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev", DATABASE=os.path.join(app.instance_path, "server.sqlite")
    )
    app.config.from_pyfile("config.py")

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/hello")
    def hello():
        return "hello"

    db.init_app(app)

    return app
