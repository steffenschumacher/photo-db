"""Tests for the headless `pdbscanner.py` CLI (scan-only, no UI)."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import pdbscanner  # noqa: E402


def test_scan_path_is_required():
    with pytest.raises(SystemExit):
        pdbscanner.parse_args([])


def test_user_without_password_errors():
    with pytest.raises(SystemExit):
        pdbscanner.parse_args(["-s", "/tmp/whatever", "-u", "alice"])


def test_password_without_user_errors():
    with pytest.raises(SystemExit):
        pdbscanner.parse_args(["-s", "/tmp/whatever", "-p", "secret"])


def test_valid_args_parse():
    args = pdbscanner.parse_args(
        ["-s", "/tmp/import", "-l", "/tmp/library", "-u", "alice", "-p", "secret"]
    )
    assert args.scanpath == "/tmp/import"
    assert args.libpath == "/tmp/library"
    assert args.user == "alice"
    assert args.password == "secret"  # pragma: allowlist secret
    assert args.debug is False


def test_debug_flag_parses():
    args = pdbscanner.parse_args(["-s", "/tmp/import", "-d"])
    assert args.debug is True


def test_main_scans_and_reports_processed_count(
    local_store_client, clean_store, test_config, capsys
):
    from .conftest import STATIC_DIR

    scan_dir = tempfile.mkdtemp()
    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as src:
        data = src.read()
    with open(f"{scan_dir}/sample.jpeg", "wb") as dst:
        dst.write(data)

    pdbscanner.main(["-s", scan_dir, "-l", test_config.STORE_URL])

    out = capsys.readouterr().out
    assert "Done - processed 1 images" in out
