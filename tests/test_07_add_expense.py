"""
Tests for Step 7 — Add Expense (spec: .claude/specs/07-add-expense.md).

Inferred/confirmed spec under test (derived from the spec file, NOT from
reading app.py's implementation line-by-line):

- GET /expenses/add:
    * Logged out -> 302 redirect to /login.
    * Logged in  -> 200, renders add_expense.html with a category dropdown
      populated from CATEGORIES (all 7: Food, Transport, Bills, Health,
      Entertainment, Shopping, Other).

- POST /expenses/add:
    * Logged out -> 302 redirect to /login, no row inserted.
    * Valid amount (positive float) + valid category (in CATEGORIES) +
      non-empty date -> inserts one expense row owned by session["user_id"]
      (never a client-supplied user_id) and redirects (302) to /profile.
    * description is optional; omitting it must not fail the request.
    * Invalid/missing amount (missing, zero, negative, non-numeric) -> 400,
      re-renders add_expense.html with an error message, NO row inserted.
    * category not in CATEGORIES -> 400, no row inserted.
    * missing/empty date -> 400, no row inserted.

- User isolation: an expense created by user A must never appear in user
  B's /profile expense list, and get_expenses_by_user(B) must not include
  A's rows.

Stub routes (/expenses/<id>/edit, /expenses/<id>/delete) are Step 8/9 and
are intentionally NOT covered here beyond what a smoke test might check
elsewhere — no behavioral assertions are made about them in this file.
"""
import sqlite3

from database.db import CATEGORIES


def _count_expenses(db_path):
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()
    conn.close()
    return row[0]


def _fetch_expenses_for_user(db_path, user_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return rows


VALID_EXPENSE_FORM = {
    "amount": "42.50",
    "category": "Food",
    "date": "2026-08-15",
    "description": "Groceries",
}


# --------------------------------------------------------------------- #
# GET /expenses/add
# --------------------------------------------------------------------- #

class TestGetAddExpense:
    def test_get_redirects_to_login_when_logged_out(self, client):
        response = client.get("/expenses/add", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_get_renders_form_when_logged_in(self, logged_in_client):
        client, _user_id = logged_in_client

        response = client.get("/expenses/add")

        assert response.status_code == 200
        assert b"amount" in response.data.lower()
        assert b"category" in response.data.lower()
        assert b"date" in response.data.lower()

    def test_get_form_includes_all_categories(self, logged_in_client):
        client, _user_id = logged_in_client

        response = client.get("/expenses/add")

        assert response.status_code == 200
        assert len(CATEGORIES) == 7
        for category in CATEGORIES:
            assert category.encode() in response.data

    def test_get_does_not_insert_a_row(self, logged_in_client, db_path):
        client, _user_id = logged_in_client

        client.get("/expenses/add")

        assert _count_expenses(db_path) == 0


# --------------------------------------------------------------------- #
# POST /expenses/add — happy path
# --------------------------------------------------------------------- #

class TestPostAddExpenseHappyPath:
    def test_valid_submission_creates_row_and_redirects_to_profile(
        self, logged_in_client, db_path
    ):
        client, user_id = logged_in_client

        response = client.post(
            "/expenses/add", data=VALID_EXPENSE_FORM, follow_redirects=False
        )

        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]

        rows = _fetch_expenses_for_user(db_path, user_id)
        assert len(rows) == 1
        assert rows[0]["amount"] == 42.50
        assert rows[0]["category"] == "Food"
        assert rows[0]["date"] == "2026-08-15"
        assert rows[0]["description"] == "Groceries"

    def test_created_expense_belongs_to_logged_in_user_not_form_supplied_id(
        self, logged_in_client, db_path
    ):
        client, user_id = logged_in_client

        # Attempt to spoof a different user_id via the form; spec requires
        # the server to always use session["user_id"], never trust form data.
        spoofed_form = dict(VALID_EXPENSE_FORM, user_id="9999")
        client.post("/expenses/add", data=spoofed_form, follow_redirects=False)

        rows = _fetch_expenses_for_user(db_path, user_id)
        assert len(rows) == 1
        assert rows[0]["user_id"] == user_id

    def test_description_is_optional(self, logged_in_client, db_path):
        client, user_id = logged_in_client
        form = {"amount": "10.00", "category": "Transport", "date": "2026-08-01"}

        response = client.post("/expenses/add", data=form, follow_redirects=False)

        assert response.status_code == 302
        rows = _fetch_expenses_for_user(db_path, user_id)
        assert len(rows) == 1
        assert rows[0]["description"] in (None, "")

    def test_new_expense_appears_on_profile_page(self, logged_in_client):
        client, _user_id = logged_in_client

        client.post("/expenses/add", data=VALID_EXPENSE_FORM, follow_redirects=True)
        profile_response = client.get("/profile")

        assert profile_response.status_code == 200
        assert b"Groceries" in profile_response.data
        assert b"Food" in profile_response.data


# --------------------------------------------------------------------- #
# POST /expenses/add — validation failures
# --------------------------------------------------------------------- #

class TestPostAddExpenseValidation:
    def test_missing_amount_returns_400_and_does_not_insert(
        self, logged_in_client, db_path
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM)
        del form["amount"]

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        assert _count_expenses(db_path) == 0

    def test_zero_amount_returns_400_and_does_not_insert(
        self, logged_in_client, db_path
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM, amount="0")

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        assert _count_expenses(db_path) == 0

    def test_negative_amount_returns_400_and_does_not_insert(
        self, logged_in_client, db_path
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM, amount="-15.00")

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        assert _count_expenses(db_path) == 0

    def test_non_numeric_amount_returns_400_and_does_not_insert(
        self, logged_in_client, db_path
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM, amount="not-a-number")

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        assert _count_expenses(db_path) == 0

    def test_validation_failure_rerenders_form_with_error_message(
        self, logged_in_client
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM, amount="-1")

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        # Re-renders the add_expense form (not a redirect) with an error.
        assert b"category" in response.data.lower()
        assert b"error" in response.data.lower() or b"invalid" in response.data.lower() \
            or b"valid" in response.data.lower()

    def test_category_not_in_categories_returns_400_and_does_not_insert(
        self, logged_in_client, db_path
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM, category="Vacation")

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        assert _count_expenses(db_path) == 0

    def test_missing_category_returns_400_and_does_not_insert(
        self, logged_in_client, db_path
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM)
        del form["category"]

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        assert _count_expenses(db_path) == 0

    def test_missing_date_returns_400_and_does_not_insert(
        self, logged_in_client, db_path
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM)
        del form["date"]

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        assert _count_expenses(db_path) == 0

    def test_empty_date_returns_400_and_does_not_insert(
        self, logged_in_client, db_path
    ):
        client, _user_id = logged_in_client
        form = dict(VALID_EXPENSE_FORM, date="")

        response = client.post("/expenses/add", data=form)

        assert response.status_code == 400
        assert _count_expenses(db_path) == 0


# --------------------------------------------------------------------- #
# POST /expenses/add — auth boundary
# --------------------------------------------------------------------- #

class TestPostAddExpenseAuth:
    def test_post_while_logged_out_redirects_to_login_and_does_not_insert(
        self, client, db_path
    ):
        response = client.post(
            "/expenses/add", data=VALID_EXPENSE_FORM, follow_redirects=False
        )

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]
        assert _count_expenses(db_path) == 0


# --------------------------------------------------------------------- #
# User isolation
# --------------------------------------------------------------------- #

class TestUserIsolation:
    def test_expense_created_by_user_a_not_visible_to_user_b(
        self, logged_in_client, second_user, db_path, app
    ):
        client_a, user_a_id = logged_in_client
        user_b_id = second_user

        client_a.post("/expenses/add", data=VALID_EXPENSE_FORM, follow_redirects=False)

        # Query DB helper directly for user B — must be empty.
        from database.db import get_expenses_by_user

        b_expenses = get_expenses_by_user(user_b_id)
        assert len(b_expenses) == 0

        a_expenses = get_expenses_by_user(user_a_id)
        assert len(a_expenses) == 1

    def test_user_b_profile_page_does_not_show_user_a_expense(
        self, logged_in_client, second_user, db_path, app
    ):
        client_a, _user_a_id = logged_in_client
        client_a.post("/expenses/add", data=VALID_EXPENSE_FORM, follow_redirects=False)

        # Log in as the already-registered second user via a separate
        # client/session so we don't disturb client_a's session.
        with app.test_client() as client_b:
            client_b.post(
                "/login",
                data={"email": "other@example.com", "password": "password456"},
                follow_redirects=False,
            )

            profile_response = client_b.get("/profile")

            assert profile_response.status_code == 200
            assert b"Groceries" not in profile_response.data
            assert b"No expenses yet" in profile_response.data or b"empty" in profile_response.data.lower()

    def test_empty_state_message_when_user_has_no_expenses(self, logged_in_client):
        client, _user_id = logged_in_client

        response = client.get("/profile")

        assert response.status_code == 200
        assert b"No expenses yet" in response.data or b"no expenses" in response.data.lower()
