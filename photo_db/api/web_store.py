from datetime import UTC, datetime
from hashlib import sha256
from json import loads

from flask import Flask, Response, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.exceptions import NotFound

from ..config import Config, default_config
from ..exceptions import DuplicateException
from ..photo import Photo
from ..store.logic import LocalStore


def add_routes(app: Flask, config: Config = default_config):
    store = LocalStore(config)
    auth = HTTPBasicAuth()

    @app.errorhandler(DuplicateException)
    def handle_duplicate(err: DuplicateException):
        # DuplicateException/SimilarException are plain, framework-free
        # exceptions (see photo_db.exceptions) so core scanning/storage
        # code doesn't need werkzeug installed - translate them into the
        # HTTP 409 + JSON wire format WebPDBClient.process_response expects.
        return Response(err.to_json(), status=err.code, mimetype="application/json")

    @auth.verify_password
    def authenticate(username, password):
        if username and password:
            return username == config.STORE_USER and password == config.STORE_PASS
        return False

    print("Setting up app routes..")
    print(config.info())

    @app.route("/pre_check", methods=["POST"])
    @auth.login_required
    def pre_check():
        jsn = request.json
        if isinstance(jsn, str):
            jsn = loads(jsn)
        ph = Photo(**jsn, config=config)
        store.check_hash(ph)
        return "OK"

    @app.route("/upload", methods=["POST"])
    @auth.login_required
    def upload():
        return store.upload(request.data)

    @app.route("/image/<uuid>", methods=["GET"])
    @auth.login_required
    def fetch_image(uuid: str) -> bytes:
        if ph := store.get_photo(uuid):
            data, ext = store.get_display_bytes(ph)
            # A plain Response with the bytes already in memory, rather than
            # send_file(BytesIO(...)), deliberately avoids Werkzeug's
            # wsgi.file_wrapper path: some WSGI servers (uWSGI in particular)
            # provide a file_wrapper that tries to os.sendfile() the
            # response, which doesn't work for an in-memory BytesIO (no real
            # fd) and manifests as "broken pipe"/SIGPIPE errors server-side
            # even though the data is perfectly fine - every request fails
            # that way, not just slow/large ones.
            response = Response(data, mimetype=f"image/{ext.lower()}")
            response.headers["Content-Disposition"] = f'inline; filename="{ph.filename()}"'
            return response
        raise NotFound(f"No image with uuid: {uuid}")

    @app.route("/thumb/<uuid>", methods=["GET"])
    @auth.login_required
    def fetch_thumbnail(uuid: str) -> bytes:
        if ph := store.get_photo(uuid):
            data = store.get_thumbnail(ph)
            response = Response(data, mimetype="image/jpeg")
            response.headers["Content-Disposition"] = f'inline; filename="{uuid}_thumb.jpg"'
            # Keep the ETag compact. The base64 perceptual hash is ~6.5 KiB
            # at the default 70x70 hash size; putting it directly in a
            # response header exceeds Nginx's default uWSGI header buffer
            # and turns an otherwise-successful upstream response into a
            # 502. Its digest remains stable while fitting comfortably.
            response.set_etag(sha256(ph.hash.encode()).hexdigest())
            return response
        raise NotFound(f"No image with uuid: {uuid}")

    @app.route("/meta/<uuid>", methods=["GET"])
    @auth.login_required
    def meta_image(uuid: str):
        if ph := store.get_photo(uuid):
            data = ph.model_dump()
            if ph.date:
                data["date"] = ph.date.timestamp()
            if ph.scanned:
                data["scanned"] = ph.scanned.timestamp()
            return data
        raise NotFound(f"No image with uuid: {uuid}")

    @app.route("/rotate/<uuid>", methods=["POST"])
    @auth.login_required
    def rotate(uuid: str):
        jsn = request.json or {}
        delta = int(jsn.get("delta", 90))
        if ph := store.rotate(uuid, delta):
            return {"rotation": ph.rotation}
        raise NotFound(f"No image with uuid: {uuid}")

    @app.route("/hashes", methods=["GET"])
    @auth.login_required
    def hashes() -> dict[str, str]:
        return store.get_hashes()

    @app.route("/sync", methods=["GET"])
    @auth.login_required
    def sync():
        """Lean incremental metadata sync for thick clients: cheap fields
        only (no image bytes), so a client can determine locally whether a
        candidate photo is already in the library (and browse/preview via
        /thumb/<uuid>) without a network round trip per file."""
        since_param = request.args.get("since")
        after_uuid = None
        if since_param and ":" in since_param:
            timestamp, after_uuid = since_param.split(":", 1)
            since = datetime.fromtimestamp(float(timestamp), tz=UTC)
        else:
            since = datetime.fromtimestamp(float(since_param), tz=UTC) if since_param else None
        limit = int(request.args.get("limit", 5000))
        photos = store.since(since, limit, after_uuid)
        return {
            "photos": [ph.lean_dict() for ph in photos],
            "next_since": (
                f"{int(photos[-1].scanned.timestamp())}:{photos[-1].uuid}"
                if photos
                else since_param
            ),
        }

    @app.route("/web-config", methods=["GET"])
    @auth.login_required
    def web_config():
        """Publicly safe algorithm settings needed by browser clients."""
        return {"hash_size": config.HASH_SIZE, "similarity": config.SIMILARITY}
