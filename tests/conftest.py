"""
Shared pytest fixtures for Spendly.

Isolation strategy
-------------------
`database/db.py` defines a module-level `DB_PATH` constant that every helper
(`get_db`, `init_db`, `seed_db`, `create_user`, ...) reads from at call time.
`app.py` also calls `init_db()` / `seed_db()` once at *import* time (module
level, inside `with app.app_context(): ...`). To guarantee tests never touch
the real `expense_tracker.db` at the project root, we monkeypatch
`database.db.DB_PATH` to a temporary file path *before* `app` is imported for
the first time, using a session-scoped fixture combined with `pytest`'s
built-in `monkeypatch` (via `monkeypatch.setattr` inside a fixture that
imports `database.db` first, patches it, and only then imports `app`).

Each test function gets a fresh temp DB file (function-scoped `db_path`
fixture) so tests never share state or leak data between each other.
"""
import importlib
import sys

import pytest


@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    """Point database.db.DB_PATH at a fresh temp-file SQLite DB for this test."""
    test_db_file = tmp_path / "test_expense_tracker.db"

    import database.db as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db_file)
    return test_db_file


@pytest.fixture()
def app(db_path, monkeypatch):
    """
    A Flask app instance wired to the isolated temp DB.

    We reload app.py's module fresh for every test so that its
    module-level `init_db()` / `seed_db()` calls run against the patched
    DB_PATH from the `db_path` fixture, rather than reusing a previously
    imported (and possibly differently-configured) app module.
    """
    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")

    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret-key")

    yield app_module.app

    sys.modules.pop("app", None)


@pytest.fixture()
def client(app):
    """Flask test client for the isolated app instance."""
    return app.test_client()


def _register_and_login(client, name, email, password):
    client.post(
        "/register",
        data={"name": name, "email": email, "password": password},
        follow_redirects=False,
    )
    client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def _get_user_id_by_email(email, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row["id"] if row else None


@pytest.fixture()
def logged_in_client(client, db_path):
    """
    A test client with an authenticated session for a freshly-registered
    user ("Test User" / test@example.com). Returns (client, user_id).
    """
    email = "test@example.com"
    _register_and_login(client, "Test User", email, "password123")
    user_id = _get_user_id_by_email(email, db_path)
    return client, user_id


@pytest.fixture()
def second_user(app, db_path):
    """
    Registers a second, distinct user directly (without logging in as them,
    and without disturbing the primary client's session) for cross-user
    isolation tests. Returns the new user's id.
    """
    with app.test_client() as other_client:
        other_client.post(
            "/register",
            data={
                "name": "Other User",
                "email": "other@example.com",
                "password": "password456",
            },
            follow_redirects=False,
        )
    return _get_user_id_by_email("other@example.com", db_path)
