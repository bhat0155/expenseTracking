"""
Tests for Step 9 -- Delete Expense.

Spec under test: .claude/specs/09-delete-expense.md

These tests are derived from the SPEC's stated routes, access rules, and
Definition of Done checklist -- NOT from reading app.py's implementation and
mirroring whatever it happens to do. app.py / database/db.py /
templates/delete_expense.html were consulted only to confirm function names,
route paths, and template field names so the tests are syntactically correct
and importable.

Inferred behavior under test, per the spec:

Routes -- both GET and POST handled by a single `delete_expense(id)` view.

Access rules (apply to both GET and POST):
- Logged out -> redirect to /login (matches edit_expense, add_expense, profile).
- Expense does not exist (e.g. id 999999) -> abort(404).
- Expense exists but belongs to a different user -> abort(404), NOT 403
  (must not leak existence of another user's expense).

GET /expenses/<id>/delete (owner, logged in):
- 200, renders delete_expense.html showing the expense's date, category,
  description, and amount. Must NOT delete the row (GET never mutates data).

POST /expenses/<id>/delete (owner, logged in):
- Deletes the row from SQLite and redirects (302) to /profile, where the
  expense no longer appears. Deleting one expense must not affect others.

profile.html's expense rows link to url_for('delete_expense', id=...).
"""
import sqlite3

from database.db import create_expense


def _fetch_expense(db_path, expense_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?", (expense_id,)
    ).fetchone()
    conn.close()
    return row


def _seed_expense(user_id, amount=25.00, category="Food", date="2026-08-01",
                   description="Original description"):
    """Insert an expense directly via the DB layer (not via the add_expense
    route) so these tests don't depend on Step 7 continuing to work."""
    create_expense(user_id, amount, category, date, description)


def _expense_id_for_user(db_path, user_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["id"] if row else None


# --------------------------------------------------------------------- #
# Auth boundary -- logged out
# --------------------------------------------------------------------- #

class TestDeleteExpenseLoggedOut:
    def test_get_redirects_to_login_when_logged_out(
        self, client, second_user, db_path, app
    ):
        with app.app_context():
            _seed_expense(user_id=second_user)
        expense_id = _expense_id_for_user(db_path, second_user)

        response = client.get(f"/expenses/{expense_id}/delete", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_post_redirects_to_login_when_logged_out_and_does_not_delete_row(
        self, client, second_user, db_path, app
    ):
        with app.app_context():
            _seed_expense(user_id=second_user)
        expense_id = _expense_id_for_user(db_path, second_user)

        response = client.post(f"/expenses/{expense_id}/delete", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

        after = _fetch_expense(db_path, expense_id)
        assert after is not None


# --------------------------------------------------------------------- #
# GET /expenses/<id>/delete -- owner
# --------------------------------------------------------------------- #

class TestGetDeleteExpenseOwner:
    def test_get_renders_confirmation_page_with_expense_details(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(
                user_id=user_id,
                amount=55.25,
                category="Bills",
                date="2026-07-04",
                description="Electric bill",
            )
        expense_id = _expense_id_for_user(db_path, user_id)

        response = client.get(f"/expenses/{expense_id}/delete")

        assert response.status_code == 200
        assert b"55.25" in response.data
        assert b"Bills" in response.data
        assert b"2026-07-04" in response.data
        assert b"Electric bill" in response.data

    def test_get_does_not_delete_the_expense(self, logged_in_client, db_path, app):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, amount=10.00, category="Food")
        expense_id = _expense_id_for_user(db_path, user_id)

        response = client.get(f"/expenses/{expense_id}/delete")

        assert response.status_code == 200
        after = _fetch_expense(db_path, expense_id)
        assert after is not None
        assert after["amount"] == 10.00


# --------------------------------------------------------------------- #
# GET/POST /expenses/<id>/delete -- ownership + existence (404 boundary)
# --------------------------------------------------------------------- #

class TestDeleteExpenseOwnershipAndExistence:
    def test_get_nonexistent_expense_returns_404(self, logged_in_client):
        client, _user_id = logged_in_client

        response = client.get("/expenses/999999/delete")

        assert response.status_code == 404

    def test_post_nonexistent_expense_returns_404(self, logged_in_client):
        client, _user_id = logged_in_client

        response = client.post("/expenses/999999/delete")

        assert response.status_code == 404

    def test_get_another_users_expense_returns_404_not_403(
        self, logged_in_client, second_user, db_path, app
    ):
        client, _user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=second_user, amount=15.00, category="Health")
        other_expense_id = _expense_id_for_user(db_path, second_user)

        response = client.get(f"/expenses/{other_expense_id}/delete")

        assert response.status_code == 404
        # Must not leak the other user's data into the response.
        assert b"15.0" not in response.data

    def test_post_another_users_expense_returns_404_and_does_not_delete_it(
        self, logged_in_client, second_user, db_path, app
    ):
        client, _user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=second_user, amount=15.00, category="Health")
        other_expense_id = _expense_id_for_user(db_path, second_user)

        response = client.post(f"/expenses/{other_expense_id}/delete")

        assert response.status_code == 404
        after = _fetch_expense(db_path, other_expense_id)
        assert after is not None


# --------------------------------------------------------------------- #
# POST /expenses/<id>/delete -- happy path
# --------------------------------------------------------------------- #

class TestPostDeleteExpenseHappyPath:
    def test_valid_post_deletes_row_and_redirects_to_profile(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, amount=25.00, category="Food")
        expense_id = _expense_id_for_user(db_path, user_id)

        response = client.post(f"/expenses/{expense_id}/delete", follow_redirects=False)

        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]

        after = _fetch_expense(db_path, expense_id)
        assert after is None

    def test_deleted_expense_no_longer_appears_on_profile_page(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(
                user_id=user_id,
                amount=25.00,
                category="Food",
                description="Groceries for the week",
            )
        expense_id = _expense_id_for_user(db_path, user_id)

        client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)
        profile_response = client.get("/profile")

        assert profile_response.status_code == 200
        assert b"Groceries for the week" not in profile_response.data

    def test_deleting_one_expense_does_not_affect_others(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, amount=25.00, category="Food")
        first_id = _expense_id_for_user(db_path, user_id)
        with app.app_context():
            _seed_expense(user_id=user_id, amount=40.00, category="Transport")
        second_id = _expense_id_for_user(db_path, user_id)

        client.post(f"/expenses/{first_id}/delete", follow_redirects=False)

        assert _fetch_expense(db_path, first_id) is None
        remaining = _fetch_expense(db_path, second_id)
        assert remaining is not None
        assert remaining["amount"] == 40.00


# --------------------------------------------------------------------- #
# profile.html wiring
# --------------------------------------------------------------------- #

class TestProfileDeleteLinks:
    def test_profile_page_links_to_correct_delete_url_for_expense(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, amount=30.00, category="Entertainment")
        expense_id = _expense_id_for_user(db_path, user_id)

        response = client.get("/profile")

        assert response.status_code == 200
        expected_path = f"/expenses/{expense_id}/delete".encode()
        assert expected_path in response.data
