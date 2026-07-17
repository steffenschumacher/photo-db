import os
import sys
import tempfile
from pathlib import Path

os.environ["PH_STORE_URL"] = tempfile.mkdtemp(prefix="photodb-web-e2e-")
os.environ["PH_STORE_USER"] = "webtest"
os.environ["PH_STORE_PASS"] = "webtest-pass"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from photo_db.app import create_app  # noqa: E402

create_app().run(host="127.0.0.1", port=5000, use_reloader=False)
