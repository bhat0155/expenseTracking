"""
Tests for Step 8 -- Edit Expense.

Spec under test: .claude/specs/08-edit-expense.md

These tests are derived from the SPEC's stated routes, access rules,
database changes, validation rules, and Definition of Done checklist --
NOT from reading app.py's implementation and mirroring whatever it happens
to do. app.py / database/db.py / templates/edit_expense.html were consulted
only to confirm function names, route paths, and template field names so
the tests are syntactically correct and importable.

Inferred behavior under test, per the spec:

Routes -- both GET and POST handled by a single `edit_expense(id)` view.

Access rules (apply to both GET and POST):
- Logged out -> redirect to /login (matches add_expense, profile).
- Expense does not exist (e.g. id 999999) -> abort(404).
- Expense exists but belongs to a different user -> abort(404), NOT 403
  (must not leak existence of another user's expense).

GET /expenses/<id>/edit (owner, logged in):
- 200, renders edit_expense.html pre-filled with the expense's current
  amount, category (selected), date, and description.

POST /expenses/<id>/edit (owner, logged in):
- Reuses the exact validation rules from add_expense: amount must parse as
  a positive float; category must be in CATEGORIES; date must be
  non-empty. description remains optional.
- Valid submission -> updates the row in SQLite (amount/category/date/
  description all reflect the new values, user_id unchanged) and redirects
  (302) to /profile, where updated values become visible.
- Invalid submission (blank/zero/negative/non-numeric amount, invalid or
  missing category, missing/empty date) -> 400, re-renders
  edit_expense.html with an error message, and does NOT modify the DB row.

profile.html's edit links point at url_for('edit_expense', id=...).

Stub routes (/expenses/<id>/delete) are Step 9 and are intentionally NOT
covered here -- no behavioral assertions are made about them in this file.
"""
import sqlite3

from database.db import CATEGORIES, create_expense


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


VALID_UPDATE_FORM = {
    "amount": "99.99",
    "category": "Transport",
    "date": "2026-08-20",
    "description": "Updated description",
}


# --------------------------------------------------------------------- #
# Auth boundary -- logged out
# --------------------------------------------------------------------- #

class TestEditExpenseLoggedOut:
    def test_get_redirects_to_login_when_logged_out(
        self, client, second_user, db_path, app
    ):
        # second_user registers a real user row (without logging in on
        # `client`) so the expense's FK is satisfiable under
        # `PRAGMA foreign_keys = ON`.
        with app.app_context():
            _seed_expense(user_id=second_user)
        expense_id = _expense_id_for_user(db_path, second_user)

        response = client.get(f"/expenses/{expense_id}/edit", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_post_redirects_to_login_when_logged_out_and_does_not_modify_db(
        self, client, second_user, db_path, app
    ):
        with app.app_context():
            _seed_expense(user_id=second_user)
        expense_id = _expense_id_for_user(db_path, second_user)
        before = _fetch_expense(db_path, expense_id)

        response = client.post(
            f"/expenses/{expense_id}/edit", data=VALID_UPDATE_FORM, follow_redirects=False
        )

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

        after = _fetch_expense(db_path, expense_id)
        assert after["amount"] == before["amount"]
        assert after["category"] == before["category"]
        assert after["date"] == before["date"]


# --------------------------------------------------------------------- #
# GET /expenses/<id>/edit -- owner
# --------------------------------------------------------------------- #

class TestGetEditExpenseOwner:
    def test_get_prefills_form_with_existing_expense_values(
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

        response = client.get(f"/expenses/{expense_id}/edit")

        assert response.status_code == 200
        assert b"55.25" in response.data
        assert b"Bills" in response.data
        assert b"2026-07-04" in response.data
        assert b"Electric bill" in response.data

    def test_get_form_includes_all_categories(self, logged_in_client, db_path, app):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id)
        expense_id = _expense_id_for_user(db_path, user_id)

        response = client.get(f"/expenses/{expense_id}/edit")

        assert response.status_code == 200
        for category in CATEGORIES:
            assert category.encode() in response.data

    def test_get_does_not_modify_the_expense(self, logged_in_client, db_path, app):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, amount=10.00, category="Food")
        expense_id = _expense_id_for_user(db_path, user_id)
        before = _fetch_expense(db_path, expense_id)

        client.get(f"/expenses/{expense_id}/edit")

        after = _fetch_expense(db_path, expense_id)
        assert after["amount"] == before["amount"]
        assert after["category"] == before["category"]
        assert after["date"] == before["date"]
        assert after["description"] == before["description"]


# --------------------------------------------------------------------- #
# GET/POST /expenses/<id>/edit -- ownership + existence (404 boundary)
# --------------------------------------------------------------------- #

class TestEditExpenseOwnershipAndExistence:
    def test_get_nonexistent_expense_returns_404(self, logged_in_client):
        client, _user_id = logged_in_client

        response = client.get("/expenses/999999/edit")

        assert response.status_code == 404

    def test_post_nonexistent_expense_returns_404(self, logged_in_client):
        client, _user_id = logged_in_client

        response = client.post("/expenses/999999/edit", data=VALID_UPDATE_FORM)

        assert response.status_code == 404

    def test_get_another_users_expense_returns_404_not_403(
        self, logged_in_client, second_user, db_path, app
    ):
        client, _user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=second_user, amount=15.00, category="Health")
        other_expense_id = _expense_id_for_user(db_path, second_user)

        response = client.get(f"/expenses/{other_expense_id}/edit")

        assert response.status_code == 404
        # Must not leak the other user's data into the response.
        assert b"15.0" not in response.data

    def test_post_another_users_expense_returns_404_and_does_not_modify_it(
        self, logged_in_client, second_user, db_path, app
    ):
        client, _user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=second_user, amount=15.00, category="Health")
        other_expense_id = _expense_id_for_user(db_path, second_user)
        before = _fetch_expense(db_path, other_expense_id)

        response = client.post(
            f"/expenses/{other_expense_id}/edit", data=VALID_UPDATE_FORM
        )

        assert response.status_code == 404

        after = _fetch_expense(db_path, other_expense_id)
        assert after["amount"] == before["amount"]
        assert after["category"] == before["category"]
        assert after["date"] == before["date"]


# --------------------------------------------------------------------- #
# POST /expenses/<id>/edit -- happy path
# --------------------------------------------------------------------- #

class TestPostEditExpenseHappyPath:
    def test_valid_submission_updates_row_and_redirects_to_profile(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(
                user_id=user_id,
                amount=25.00,
                category="Food",
                date="2026-08-01",
                description="Original description",
            )
        expense_id = _expense_id_for_user(db_path, user_id)

        response = client.post(
            f"/expenses/{expense_id}/edit", data=VALID_UPDATE_FORM, follow_redirects=False
        )

        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]

        after = _fetch_expense(db_path, expense_id)
        assert after["amount"] == 99.99
        assert after["category"] == "Transport"
        assert after["date"] == "2026-08-20"
        assert after["description"] == "Updated description"
        assert after["user_id"] == user_id

    def test_updated_values_visible_on_profile_page(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, amount=25.00, category="Food")
        expense_id = _expense_id_for_user(db_path, user_id)

        client.post(f"/expenses/{expense_id}/edit", data=VALID_UPDATE_FORM, follow_redirects=True)
        profile_response = client.get("/profile")

        assert profile_response.status_code == 200
        assert b"Updated description" in profile_response.data
        assert b"Transport" in profile_response.data

    def test_description_can_be_cleared_to_optional(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, description="Has a description")
        expense_id = _expense_id_for_user(db_path, user_id)

        form = {"amount": "12.00", "category": "Shopping", "date": "2026-08-10"}
        response = client.post(
            f"/expenses/{expense_id}/edit", data=form, follow_redirects=False
        )

        assert response.status_code == 302
        after = _fetch_expense(db_path, expense_id)
        assert after["description"] in (None, "")

    def test_expense_id_is_not_reassignable_via_form(
        self, logged_in_client, db_path, app
    ):
        """The route's URL segment identifies which row to update; nothing
        in the form should let the client redirect the update elsewhere."""
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, amount=25.00, category="Food")
        expense_id = _expense_id_for_user(db_path, user_id)

        spoofed_form = dict(VALID_UPDATE_FORM, id="999999", user_id="999999")
        client.post(f"/expenses/{expense_id}/edit", data=spoofed_form, follow_redirects=False)

        after = _fetch_expense(db_path, expense_id)
        assert after["amount"] == 99.99
        assert after["user_id"] == user_id


# --------------------------------------------------------------------- #
# POST /expenses/<id>/edit -- validation failures
# --------------------------------------------------------------------- #

class TestPostEditExpenseValidation:
    def _seed_and_get_id(self, app, db_path, user_id):
        with app.app_context():
            _seed_expense(
                user_id=user_id,
                amount=25.00,
                category="Food",
                date="2026-08-01",
                description="Original description",
            )
        return _expense_id_for_user(db_path, user_id)

    def test_missing_amount_returns_400_and_does_not_modify(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        before = _fetch_expense(db_path, expense_id)
        form = dict(VALID_UPDATE_FORM)
        del form["amount"]

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        after = _fetch_expense(db_path, expense_id)
        assert after["amount"] == before["amount"]
        assert after["category"] == before["category"]

    def test_zero_amount_returns_400_and_does_not_modify(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        before = _fetch_expense(db_path, expense_id)
        form = dict(VALID_UPDATE_FORM, amount="0")

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        after = _fetch_expense(db_path, expense_id)
        assert after["amount"] == before["amount"]

    def test_negative_amount_returns_400_and_does_not_modify(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        before = _fetch_expense(db_path, expense_id)
        form = dict(VALID_UPDATE_FORM, amount="-15.00")

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        after = _fetch_expense(db_path, expense_id)
        assert after["amount"] == before["amount"]

    def test_non_numeric_amount_returns_400_and_does_not_modify(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        before = _fetch_expense(db_path, expense_id)
        form = dict(VALID_UPDATE_FORM, amount="not-a-number")

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        after = _fetch_expense(db_path, expense_id)
        assert after["amount"] == before["amount"]

    def test_invalid_category_returns_400_and_does_not_modify(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        before = _fetch_expense(db_path, expense_id)
        form = dict(VALID_UPDATE_FORM, category="Vacation")

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        after = _fetch_expense(db_path, expense_id)
        assert after["category"] == before["category"]

    def test_missing_category_returns_400_and_does_not_modify(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        before = _fetch_expense(db_path, expense_id)
        form = dict(VALID_UPDATE_FORM)
        del form["category"]

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        after = _fetch_expense(db_path, expense_id)
        assert after["category"] == before["category"]

    def test_missing_date_returns_400_and_does_not_modify(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        before = _fetch_expense(db_path, expense_id)
        form = dict(VALID_UPDATE_FORM)
        del form["date"]

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        after = _fetch_expense(db_path, expense_id)
        assert after["date"] == before["date"]

    def test_empty_date_returns_400_and_does_not_modify(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        before = _fetch_expense(db_path, expense_id)
        form = dict(VALID_UPDATE_FORM, date="")

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        after = _fetch_expense(db_path, expense_id)
        assert after["date"] == before["date"]

    def test_validation_failure_rerenders_edit_form_with_error_message(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        expense_id = self._seed_and_get_id(app, db_path, user_id)
        form = dict(VALID_UPDATE_FORM, amount="-1")

        response = client.post(f"/expenses/{expense_id}/edit", data=form)

        assert response.status_code == 400
        # Re-renders the edit form (not a redirect) with an error, still
        # showing the (pre-existing) expense's category options.
        assert b"category" in response.data.lower()
        assert b"error" in response.data.lower() or b"invalid" in response.data.lower() \
            or b"valid" in response.data.lower()


# --------------------------------------------------------------------- #
# profile.html wiring
# --------------------------------------------------------------------- #

class TestProfileEditLinks:
    def test_profile_page_links_to_correct_edit_url_for_expense(
        self, logged_in_client, db_path, app
    ):
        client, user_id = logged_in_client
        with app.app_context():
            _seed_expense(user_id=user_id, amount=30.00, category="Entertainment")
        expense_id = _expense_id_for_user(db_path, user_id)

        response = client.get("/profile")

        assert response.status_code == 200
        expected_path = f"/expenses/{expense_id}/edit".encode()
        assert expected_path in response.data
