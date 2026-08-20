"""
Tests for Step 7: Add Expense On Profile.

Spec under test: .claude/specs/07-add-expense-on-profile.md

Inferred behavioral spec (tests are written against this, not the
implementation):

- POST /expenses/add is the only method registered for this URL; a bare
  GET /expenses/add must now 405 (the old stub is gone).
- Auth guard: if session["user_id"] is not set, POST /expenses/add must
  redirect to GET /login (via url_for("login")) and must NOT insert a
  row into expenses.
- Happy path: a logged-in user POSTing valid amount/category/date
  (description optional) causes exactly one new row to be inserted into
  `expenses` with user_id = session["user_id"], and the response is a
  redirect to GET /profile. The new expense should then appear when
  /profile is subsequently loaded.
- Validation (server-side, independent of HTML5 client hints):
    * amount is required and must parse as a positive float
      (missing, blank, "0", negative, and non-numeric amounts are all
      invalid)
    * category is required and must be a member of CATEGORIES
    * date is required
    * description is optional
  On any validation failure: no row is inserted, the response re-renders
  profile.html (NOT a redirect) with status 400, an error message is
  present, and the user's account details / existing expenses are still
  shown (nothing is lost).
- Ownership: the expense is always attributed to session["user_id"];
  even if a malicious caller supplies a `user_id` field in the POST
  body, the inserted row's user_id must be the session user, never the
  form-supplied value. Other users' expenses must never be touched.
- categories passed to the template for the dropdown must match
  database.db.CATEGORIES exactly.

Fixtures isolate all DB state in a temp SQLite file (via monkeypatching
database.db.DB_PATH) so tests never touch the developer's real
expense_tracker.db, and each test gets a fresh schema.
"""

import sqlite3
from pathlib import Path

import pytest

import app as app_module
import database.db as db


@pytest.fixture
def temp_db_path(tmp_path, monkeypatch):
    """Point database.db.DB_PATH at an isolated temp file for this test."""
    test_db_file = tmp_path / "test_expense_tracker.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_file)
    return test_db_file


@pytest.fixture
def client(temp_db_path):
    """Flask test client backed by a fresh, isolated SQLite DB (no seed data)."""
    app_module.app.config["TESTING"] = True

    with app_module.app.app_context():
        db.init_db()
        # Intentionally do NOT call seed_db() — tests create their own
        # fixed set of users/expenses so assertions aren't coupled to
        # demo seed data.

    with app_module.app.test_client() as test_client:
        yield test_client


def create_test_user(name="Alice", email="alice@example.com", password="hunter2hunter"):
    from werkzeug.security import generate_password_hash

    return db.create_user(name, email, generate_password_hash(password))


def login_as(client, user_id):
    """Directly set the session, bypassing the login route/UI."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def fetch_all_expenses():
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM expenses").fetchall()
    conn.close()
    return rows


# --------------------------------------------------------------------- #
# GET /expenses/add no longer exists as a page                          #
# --------------------------------------------------------------------- #

def test_get_expenses_add_returns_405(client):
    response = client.get("/expenses/add")

    assert response.status_code == 405


# --------------------------------------------------------------------- #
# Auth guard                                                             #
# --------------------------------------------------------------------- #

def test_post_expense_while_logged_out_redirects_to_login(client):
    response = client.post(
        "/expenses/add",
        data={
            "amount": "25.00",
            "category": "Food",
            "date": "2026-08-01",
            "description": "Snacks",
        },
    )

    assert response.status_code in (301, 302, 303, 307, 308)
    assert "/login" in response.location


def test_post_expense_while_logged_out_does_not_insert_row(client):
    client.post(
        "/expenses/add",
        data={
            "amount": "25.00",
            "category": "Food",
            "date": "2026-08-01",
            "description": "Snacks",
        },
    )

    assert len(fetch_all_expenses()) == 0


# --------------------------------------------------------------------- #
# Happy path                                                             #
# --------------------------------------------------------------------- #

def test_valid_submission_redirects_to_profile(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2026-08-15",
            "description": "Groceries",
        },
    )

    assert response.status_code in (301, 302, 303, 307, 308)
    assert response.location.endswith("/profile")


def test_valid_submission_inserts_row_with_correct_fields(client):
    user_id = create_test_user()
    login_as(client, user_id)

    client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2026-08-15",
            "description": "Groceries",
        },
    )

    rows = fetch_all_expenses()
    assert len(rows) == 1
    row = rows[0]
    assert row["user_id"] == user_id
    assert row["amount"] == pytest.approx(42.50)
    assert row["category"] == "Food"
    assert row["date"] == "2026-08-15"
    assert row["description"] == "Groceries"


def test_valid_submission_without_description_still_inserts(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "10.00",
            "category": "Transport",
            "date": "2026-08-16",
        },
    )

    assert response.status_code in (301, 302, 303, 307, 308)
    rows = fetch_all_expenses()
    assert len(rows) == 1
    assert rows[0]["category"] == "Transport"


def test_new_expense_appears_on_profile_page_after_redirect(client):
    user_id = create_test_user()
    login_as(client, user_id)

    client.post(
        "/expenses/add",
        data={
            "amount": "15.25",
            "category": "Entertainment",
            "date": "2026-08-10",
            "description": "Movie night",
        },
    )

    response = client.get("/profile")

    assert response.status_code == 200
    assert b"Movie night" in response.data


# --------------------------------------------------------------------- #
# Validation: amount                                                    #
# --------------------------------------------------------------------- #

def test_missing_amount_rerenders_profile_with_400_and_no_insert(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "",
            "category": "Food",
            "date": "2026-08-15",
        },
    )

    assert response.status_code == 400
    assert len(fetch_all_expenses()) == 0


def test_zero_amount_is_rejected(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "0",
            "category": "Food",
            "date": "2026-08-15",
        },
    )

    assert response.status_code == 400
    assert len(fetch_all_expenses()) == 0


def test_negative_amount_is_rejected(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "-5.00",
            "category": "Food",
            "date": "2026-08-15",
        },
    )

    assert response.status_code == 400
    assert len(fetch_all_expenses()) == 0


def test_non_numeric_amount_is_rejected(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "not-a-number",
            "category": "Food",
            "date": "2026-08-15",
        },
    )

    assert response.status_code == 400
    assert len(fetch_all_expenses()) == 0


def test_validation_error_response_contains_error_message(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "-5.00",
            "category": "Food",
            "date": "2026-08-15",
        },
    )

    # profile.html surfaces server-side errors via the .auth-error pattern
    assert b"error" in response.data.lower() or b"auth-error" in response.data


# --------------------------------------------------------------------- #
# Validation: category                                                  #
# --------------------------------------------------------------------- #

def test_missing_category_is_rejected(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "10.00",
            "category": "",
            "date": "2026-08-15",
        },
    )

    assert response.status_code == 400
    assert len(fetch_all_expenses()) == 0


def test_category_not_in_categories_is_rejected(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "10.00",
            "category": "NotARealCategory",
            "date": "2026-08-15",
        },
    )

    assert response.status_code == 400
    assert len(fetch_all_expenses()) == 0


# --------------------------------------------------------------------- #
# Validation: date                                                      #
# --------------------------------------------------------------------- #

def test_missing_date_is_rejected(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "10.00",
            "category": "Food",
            "date": "",
        },
    )

    assert response.status_code == 400
    assert len(fetch_all_expenses()) == 0


# --------------------------------------------------------------------- #
# Validation errors preserve page context                               #
# --------------------------------------------------------------------- #

def test_validation_error_still_shows_account_details(client):
    user_id = create_test_user(name="Alice Example", email="alice@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "bad",
            "category": "Food",
            "date": "2026-08-15",
        },
    )

    assert response.status_code == 400
    assert b"Alice Example" in response.data


def test_validation_error_still_shows_existing_expenses(client):
    user_id = create_test_user()
    login_as(client, user_id)
    db.create_expense(user_id, 99.99, "Bills", "2026-08-01", "Rent")

    response = client.post(
        "/expenses/add",
        data={
            "amount": "bad",
            "category": "Food",
            "date": "2026-08-15",
        },
    )

    assert response.status_code == 400
    assert b"Rent" in response.data


# --------------------------------------------------------------------- #
# Ownership / scoping                                                   #
# --------------------------------------------------------------------- #

def test_expense_is_attributed_to_session_user_not_form_user_id(client):
    owner_id = create_test_user(name="Owner", email="owner@example.com")
    other_id = create_test_user(name="Other", email="other@example.com")
    login_as(client, owner_id)

    client.post(
        "/expenses/add",
        data={
            "amount": "10.00",
            "category": "Food",
            "date": "2026-08-15",
            "user_id": str(other_id),  # attempted spoof
        },
    )

    rows = fetch_all_expenses()
    assert len(rows) == 1
    assert rows[0]["user_id"] == owner_id
    assert rows[0]["user_id"] != other_id


def test_adding_expense_does_not_affect_other_users_expenses(client):
    user_a = create_test_user(name="A", email="a@example.com")
    user_b = create_test_user(name="B", email="b@example.com")

    db.create_expense(user_b, 50.00, "Shopping", "2026-08-01", "B's expense")

    login_as(client, user_a)
    client.post(
        "/expenses/add",
        data={
            "amount": "20.00",
            "category": "Food",
            "date": "2026-08-15",
            "description": "A's expense",
        },
    )

    b_expenses = db.get_expenses_by_user(user_b)
    assert len(b_expenses) == 1
    assert b_expenses[0]["description"] == "B's expense"

    a_expenses = db.get_expenses_by_user(user_a)
    assert len(a_expenses) == 1
    assert a_expenses[0]["description"] == "A's expense"


# --------------------------------------------------------------------- #
# Category dropdown data                                                #
# --------------------------------------------------------------------- #

def test_profile_page_category_options_match_categories_constant(client):
    user_id = create_test_user()
    login_as(client, user_id)

    response = client.get("/profile")

    assert response.status_code == 200
    for category in db.CATEGORIES:
        assert category.encode() in response.data
