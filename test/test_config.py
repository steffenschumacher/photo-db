"""Tests for Config as an instantiable, dependency-injectable object.

Config used to be a class with attributes read once from the environment at
import time (shared, mutable, global state - impossible to isolate between
tests or use multiple stores in one process). It is now instantiated
explicitly, with each instance independent.
"""

import tempfile

from photo_db.client.local_client import LocalPDBClient
from photo_db.config import Config, default_config

from .conftest import STATIC_DIR


def test_config_instances_are_independent():
    a = Config(store_url=tempfile.mkdtemp())
    b = Config(store_url=tempfile.mkdtemp())
    assert a.STORE_URL != b.STORE_URL

    a.STORE_URL = "/mutated/only/on/a"
    assert b.STORE_URL != "/mutated/only/on/a"


def test_config_overrides_take_precedence_over_env(monkeypatch):
    monkeypatch.setenv("PH_HASH_SIZE", "42")
    cfg = Config(hash_size=99)
    assert cfg.HASH_SIZE == 99

    cfg_from_env = Config()
    assert cfg_from_env.HASH_SIZE == 42


def test_debug_defaults_off_and_can_be_enabled(monkeypatch):
    monkeypatch.delenv("PH_DEBUG", raising=False)
    assert Config().DEBUG is False
    assert Config(debug=True).DEBUG is True


def test_diff_limit_uses_this_instances_similarity():
    strict = Config(store_url=tempfile.mkdtemp(), similarity=99)
    lenient = Config(store_url=tempfile.mkdtemp(), similarity=50)
    assert strict.diff_limit() < lenient.diff_limit()


def test_info_redacts_password():
    cfg = Config(store_url=tempfile.mkdtemp(), store_pass="super-secret")
    assert "super-secret" not in cfg.info()
    assert "***" in cfg.info()


def test_two_local_stores_are_fully_isolated():
    config_a = Config(store_url=tempfile.mkdtemp())
    config_b = Config(store_url=tempfile.mkdtemp())
    client_a = LocalPDBClient(config_a)
    client_b = LocalPDBClient(config_b)

    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as f:
        img_data = f.read()
    client_a.upload(img_data)

    assert len(client_a.hashes()) == 1
    assert len(client_b.hashes()) == 0


def test_default_config_is_a_singleton_instance():
    assert isinstance(default_config, Config)
