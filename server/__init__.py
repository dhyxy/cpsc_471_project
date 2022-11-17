import os

from flask import Flask

from server import db


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev", DATABASE=os.path.join(app.instance_path, "server.sqlite")
    )
    app.config.from_pyfile("config.py")
    os.makedirs(app.instance_path, exist_ok=True)

    if app.debug:
        app.config['EXPLAIN_TEMPLATE_LOADING'] = True

    from server.app import core
    app.register_blueprint(core)

    db.init_app(app)
    return app
