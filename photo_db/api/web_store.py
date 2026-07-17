from io import BytesIO
from json import loads
from flask import Flask, request, send_file
from flask_httpauth import HTTPBasicAuth
from werkzeug.exceptions import NotFound
from ..config import Config
from ..photo import Photo


auth = HTTPBasicAuth()


@auth.verify_password
def authenticate(username, password):
    if username and password:
        return username == Config.STORE_USER and password == Config.STORE_PASS
    return False


def add_routes(app: Flask):
    from photo_db.store.logic import LocalStore

    print(f"Setting up app routes..")
    print(Config.info())

    @app.route("/pre_check", methods=["POST"])
    @auth.login_required
    def pre_check():
        jsn = request.json
        if isinstance(jsn, str):
            jsn = loads(jsn)
        ph = Photo(**jsn)
        LocalStore.check_hash(ph)
        return "OK"

    @app.route("/upload", methods=["POST"])
    @auth.login_required
    def upload():
        return LocalStore.upload(request.data)

    @app.route("/image/<uuid>", methods=["GET"])
    @auth.login_required
    def fetch_image(uuid: str) -> bytes:
        if ph := LocalStore.get_photo(uuid):
            data = LocalStore.read_photo(ph)

            return send_file(
                data,
                download_name=ph.filename(),
                mimetype=f"image/{ph.extension.lower()}",
                as_attachment=False,
            )
        raise NotFound(f"No image with uuid: {uuid}")

    @app.route("/meta/<uuid>", methods=["GET"])
    @auth.login_required
    def meta_image(uuid: str):
        if ph := LocalStore.get_photo(uuid):
            data = ph.dict()
            if ph.date:
                data["date"] = ph.date.timestamp()
            if ph.scanned:
                data["scanned"] = ph.scanned.timestamp()
            return data
        raise NotFound(f"No image with uuid: {uuid}")

    @app.route("/hashes", methods=["GET"])
    @auth.login_required
    def hashes() -> dict[str, str]:
        return LocalStore.get_hashes()
