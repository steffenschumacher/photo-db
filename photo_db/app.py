from pathlib import Path

from flask import Flask, abort, send_from_directory

from photo_db.api.web_store import add_routes


def create_app():
    package_root = Path(__file__).resolve().parent
    packaged_web_root = package_root / "web" / "browser"
    development_web_root = package_root.parent / "web-ui" / "dist" / "web-ui" / "browser"
    web_root = packaged_web_root if packaged_web_root.is_dir() else development_web_root
    app = Flask(__name__, static_folder=None)
    add_routes(app)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def web_app(path: str):
        """Serve the built Angular companion, falling back to its SPA shell."""
        if not web_root.is_dir():
            abort(404, "Angular web UI has not been built")
        requested = web_root / path
        if path and requested.is_file():
            return send_from_directory(web_root, path)
        return send_from_directory(web_root, "index.html")

    return app
