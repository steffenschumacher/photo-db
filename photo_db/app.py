from flask import Flask

from photo_db.api.web_store import add_routes


def create_app():
    app = Flask(__name__)
    add_routes(app)
    return app
