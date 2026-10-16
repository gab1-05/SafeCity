"""
Configuration-module contracts: dev/prod settings importability and
hardening, and importability of the WSGI/ASGI entry points.
"""

import importlib
import sys

import pytest


def test_dev_settings_importable(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    sys.modules.pop("config.settings.dev", None)
    mod = importlib.import_module("config.settings.dev")
    assert mod.DEBUG is True
    assert "console" in mod.EMAIL_BACKEND
    assert mod.EMAIL_NOTIFICATION_FALLBACK_TO_DB is True


def test_prod_settings_without_allowed_hosts_raises(monkeypatch):
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    sys.modules.pop("config.settings.prod", None)
    # prod.py asserts ALLOWED_HOSTS is non-empty (no default in production).
    with pytest.raises(AssertionError):
        importlib.import_module("config.settings.prod")


def test_prod_settings_hardened(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "safecity.example.com")
    sys.modules.pop("config.settings.prod", None)
    mod = importlib.import_module("config.settings.prod")
    assert mod.DEBUG is False
    assert mod.SECURE_SSL_REDIRECT is True
    assert mod.SECURE_HSTS_SECONDS == 31_536_000
    assert mod.SESSION_COOKIE_SECURE is True
    assert mod.CSRF_COOKIE_SECURE is True
    assert mod.CELERY_TASK_ALWAYS_EAGER is False


def test_wsgi_asgi_and_routing_importable():
    import config.asgi  # noqa: F401
    import config.routing  # noqa: F401
    import config.wsgi

    assert config.wsgi.application is not None
    assert config.routing.application is not None
