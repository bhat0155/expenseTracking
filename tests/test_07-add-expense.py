"""
Tests for Step 7 -- Add Expense.

Spec under test: .claude/specs/07-add-expense.md

These tests are derived from the SPEC's stated routes, database changes,
validation rules, and Definition of Done checklist -- not from reading
app.py's implementation and mirroring whatever it happens to do. app.py and
database/db.py were consulted only to confirm function names / route paths /
fixture wiring so the tests are syntactically correct and importable.

Inferred behavior under test, per the spec:

Routes
- GET /expenses/add
    * Logged out  -> redirect to GET /login (spec: "same redirect rule",
      matching the existing /profile auth pattern).
    * Logged in   -> 200, renders add_expense.html with a category dropdown
      populated from CATEGORIES (7 categories: Food, Transport, Bills,
      Health, Entertainment, Shopping, Other).
- POST /expenses/add
    * Logged out  -> redirect to /login, no row inserted (DoD item).
    * Valid amount (positive float) + category in CATEGORIES + non-empty
      date -> inserts one expenses row for session["user_id"] (never a
      client-supplied user_id -- spec: "never trust a user-supplied user_id
      from the form") and redirects to GET /profile. New expense appears at
      the top of the expense list on /profile (spec table is ordered
      `date DESC, id DESC`, so a newly added expense with today's/latest
      date should surface first).
    * description is optional (nullable column, optional form field).
    * Missing/zero/negative/non-numeric amount -> 400, re-renders
      add_expense.html with an error message, no row inserted (DoD item).
    * category not in CATEGORIES -> 400, re-renders add_expense.html with
      an error message, no row inserted (DoD item).
    * missing/empty date -> required per spec ("date ... are required") ->
      400, no row inserted.

Database
- expenses table: id, user_id (FK -> users.id, not null), amount (REAL,
  not null), category (TEXT, not null), date (TEXT, not null), description
  (TEXT, nullable), created_at (TEXT, default now).
- create_expense(user_id, amount, category, date, description) inserts a
  row; only ever called with session["user_id"], never a form-supplied id.
- get_expenses_by_user(user_id) returns only that user's rows.
- CATEGORIES constant holds exactly the 7 spec-listed categories.

Cross-cutting / DoD checklist items covered here:
- /profile shows an empty-state message when the user has no expenses.
- No other user's expenses are ever visible or affected by an insert
  (strict per-user isolation, both via the DB helper and via the rendered
  /profile page for a second user).
- All internal links/forms use url_for() -- we don't assert on this
  directly (that's a code-review/template concern) but we do assert the
  profile page contains a working link to the add-expense route and that
  add_expense.html links back to /profile, which is only possible if
  url_for() resolved correctly.

Explicitly OUT of scope (per CLAUDE.md stub-route policy):
- /expenses/<id>/edit and /expenses/<id>/delete are Step 8/9 stubs. They
  are not touched by this spec and are not tested here.

Fixtures reused from tests/conftest.py (already present in the repo):
- `client`            -- unauthenticated Flask test client, isolated temp DB
- `app`                -- Flask app instance wired to the isolated temp DB
- `db_path`            -- path to the per-test temp SQLite DB file
- `logged_in_client`   -- (client, user_id) for a freshly registered/logged
                          in "Test User" <test@example.com>
- `second_user`        -- registers a second, distinct user
                          ("Other User" <other@example.com> / password456)
                          without disturbing the primary client's session;
                          returns that user's id
"""
import sqlite3

import pytest

from database.db import CATEGORIES


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #

def _count_all_expenses(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()


def _fetch_expense_rows(db_path, user_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchall()
    finally:
        conn.close()


VALID_FORM = {
    "amount": "18.75",
    "category": "Bills",
    "date": "2026-08-10",
    "description": "Electricity bill",
}


# --------------------------------------------------------------------- #
# GET /expenses/add -- auth guard + form rendering
# --------------------------------------------------------------------- #

def test_get_add_expense_logged_out_redirects_to_login(client):
    """Spec DoD: 'Visiting /expenses/add while logged out redirects to /login'."""
    response = client.get("/expenses/add", follow_redirects=False)

    assert response.status_code in (301, 302, 303, 307, 308)
    assert "/login" in response.headers["Location"]


def test_get_add_expense_logged_out_does_not_insert_a_row(client, db_path):
    """A bare GET should never have any side effect on the expenses table."""
    client.get("/expenses/add", follow_redirects=False)

    assert _count_all_expenses(db_path) == 0


def test_get_add_expense_logged_in_renders_form_with_category_dropdown(logged_in_client):
    """Spec DoD: form with a category dropdown populated from CATEGORIES."""
    client, _user_id = logged_in_client

    response = client.get("/expenses/add")

    assert response.status_code == 200
    assert len(CATEGORIES) == 7
    for category in CATEGORIES:
        assert category.encode() in response.data


def test_get_add_expense_logged_in_has_amount_and_date_fields(logged_in_client):
    """Spec: form fields amount (number), category (select), date (date input)."""
    client, _user_id = logged_in_client

    response = client.get("/expenses/add")

    assert response.status_code == 200
    body = response.data.lower()
    assert b'name="amount"' in body
    assert b'name="category"' in body
    assert b'name="date"' in body
    assert b'name="description"' in body


# --------------------------------------------------------------------- #
# POST /expenses/add -- auth guard
# --------------------------------------------------------------------- #

def test_post_add_expense_logged_out_redirects_to_login(client):
    """Spec DoD: 'Submitting POST /expenses/add while logged out redirects to /login'."""
    response = client.post("/expenses/add", data=VALID_FORM, follow_redirects=False)

    assert response.status_code in (301, 302, 303, 307, 308)
    assert "/login" in response.headers["Location"]


def test_post_add_expense_logged_out_does_not_insert_a_row(client, db_path):
    """Spec DoD: logged-out POST 'does not insert a row'."""
    client.post("/expenses/add", data=VALID_FORM, follow_redirects=False)

    assert _count_all_expenses(db_path) == 0


# --------------------------------------------------------------------- #
# POST /expenses/add -- happy path
# --------------------------------------------------------------------- #

def test_post_valid_expense_inserts_row_and_redirects_to_profile(logged_in_client, db_path):
    """Spec DoD: valid submission creates a row and redirects to /profile."""
    client, user_id = logged_in_client

    response = client.post("/expenses/add", data=VALID_FORM, follow_redirects=False)

    assert response.status_code in (301, 302, 303, 307, 308)
    assert "/profile" in response.headers["Location"]

    rows = _fetch_expense_rows(db_path, user_id)
    assert len(rows) == 1
    assert rows[0]["user_id"] == user_id
    assert rows[0]["amount"] == pytest.approx(18.75)
    assert rows[0]["category"] == "Bills"
    assert rows[0]["date"] == "2026-08-10"
    assert rows[0]["description"] == "Electricity bill"


def test_post_valid_expense_ignores_client_supplied_user_id(logged_in_client, db_path):
    """Spec: 'Only insert the expense for session["user_id"] -- never trust
    a user-supplied user_id from the form.'"""
    client, real_user_id = logged_in_client
    spoofed_form = dict(VALID_FORM, user_id="999999")

    client.post("/expenses/add", data=spoofed_form, follow_redirects=False)

    rows = _fetch_expense_rows(db_path, real_user_id)
    assert len(rows) == 1
    assert rows[0]["user_id"] == real_user_id


def test_post_valid_expense_without_description_succeeds(logged_in_client, db_path):
    """Spec: description is nullable/optional; omitting it must not fail."""
    client, user_id = logged_in_client
    form = {"amount": "5.00", "category": "Transport", "date": "2026-08-11"}

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code in (301, 302, 303, 307, 308)
    rows = _fetch_expense_rows(db_path, user_id)
    assert len(rows) == 1
    assert rows[0]["description"] in (None, "")


def test_new_expense_appears_at_top_of_profile_list(logged_in_client):
    """Spec DoD: 'redirects to /profile, where the new expense appears at
    the top of the expense list'."""
    client, _user_id = logged_in_client

    # Add an older expense first, then a newer one -- newer should sort first
    # given the spec's ORDER BY date DESC, id DESC.
    client.post(
        "/expenses/add",
        data=dict(VALID_FORM, date="2026-01-01", description="Old expense"),
        follow_redirects=False,
    )
    client.post(
        "/expenses/add",
        data=dict(VALID_FORM, date="2026-08-19", description="Newest expense"),
        follow_redirects=False,
    )

    response = client.get("/profile")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Newest expense" in body
    assert "Old expense" in body
    assert body.index("Newest expense") < body.index("Old expense")


def test_new_expense_visible_on_profile_after_redirect(logged_in_client):
    """End-to-end happy path: submit -> follow redirect -> see it on /profile."""
    client, _user_id = logged_in_client

    response = client.post("/expenses/add", data=VALID_FORM, follow_redirects=True)

    assert response.status_code == 200
    assert b"Electricity bill" in response.data
    assert b"Bills" in response.data


# --------------------------------------------------------------------- #
# POST /expenses/add -- amount validation
# --------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "bad_amount",
    ["", "0", "0.00", "-5", "-0.01", "abc", "twenty", "12abc", "NaN"],
)
def test_post_invalid_amount_returns_400_and_does_not_insert(
    logged_in_client, db_path, bad_amount
):
    """Spec: 'amount must parse as a positive float' -- missing, zero,
    negative, and non-numeric amounts must all be rejected with a 400 and
    no DB insert."""
    client, _user_id = logged_in_client
    form = dict(VALID_FORM, amount=bad_amount)

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code == 400
    assert _count_all_expenses(db_path) == 0


def test_post_missing_amount_field_entirely_returns_400_and_does_not_insert(
    logged_in_client, db_path
):
    """amount is a required field -- omitting the form key entirely must
    also be rejected, not just an empty string."""
    client, _user_id = logged_in_client
    form = dict(VALID_FORM)
    del form["amount"]

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code == 400
    assert _count_all_expenses(db_path) == 0


def test_post_invalid_amount_rerenders_add_expense_form_with_error(logged_in_client):
    """Spec: 'On validation error, re-renders add_expense.html with an
    error message and a 400 status' -- not a redirect, and the user's form
    context (category select, etc.) must still be present."""
    client, _user_id = logged_in_client
    form = dict(VALID_FORM, amount="-1")

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code == 400
    body = response.data.lower()
    assert b"category" in body  # form re-rendered, not redirected away
    assert b"error" in body or b"invalid" in body or b"valid" in body


# --------------------------------------------------------------------- #
# POST /expenses/add -- category validation
# --------------------------------------------------------------------- #

def test_post_category_not_in_categories_returns_400_and_does_not_insert(
    logged_in_client, db_path
):
    """Spec DoD: 'Submitting with a category not in CATEGORIES re-renders
    add_expense.html with an error message and a 400 status, and does not
    insert a row.'"""
    client, _user_id = logged_in_client
    form = dict(VALID_FORM, category="Vacation")  # not in CATEGORIES

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code == 400
    assert _count_all_expenses(db_path) == 0


def test_post_missing_category_returns_400_and_does_not_insert(logged_in_client, db_path):
    """category is required (must be one of CATEGORIES); omitting it
    entirely cannot be treated as valid."""
    client, _user_id = logged_in_client
    form = dict(VALID_FORM)
    del form["category"]

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code == 400
    assert _count_all_expenses(db_path) == 0


def test_post_category_not_in_categories_rerenders_form_with_error(logged_in_client):
    """Invalid category must re-render the form (400), not redirect."""
    client, _user_id = logged_in_client
    form = dict(VALID_FORM, category="Vacation")

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code == 400
    body = response.data.lower()
    assert b"error" in body or b"invalid" in body or b"valid" in body


# --------------------------------------------------------------------- #
# POST /expenses/add -- date validation
# --------------------------------------------------------------------- #

def test_post_missing_date_returns_400_and_does_not_insert(logged_in_client, db_path):
    """Spec: 'date ... are required'."""
    client, _user_id = logged_in_client
    form = dict(VALID_FORM)
    del form["date"]

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code == 400
    assert _count_all_expenses(db_path) == 0


def test_post_empty_date_returns_400_and_does_not_insert(logged_in_client, db_path):
    client, _user_id = logged_in_client
    form = dict(VALID_FORM, date="")

    response = client.post("/expenses/add", data=form, follow_redirects=False)

    assert response.status_code == 400
    assert _count_all_expenses(db_path) == 0


# --------------------------------------------------------------------- #
# /profile -- empty state
# --------------------------------------------------------------------- #

def test_profile_shows_empty_state_when_no_expenses(logged_in_client):
    """Spec DoD: '/profile shows an empty-state message when the logged-in
    user has no expenses.'"""
    client, _user_id = logged_in_client

    response = client.get("/profile")

    assert response.status_code == 200
    body = response.data.lower()
    assert b"no expenses" in body or b"empty" in body


def test_profile_links_to_add_expense_page(logged_in_client):
    """Spec: profile.html links to /expenses/add via url_for('add_expense')."""
    client, _user_id = logged_in_client

    response = client.get("/profile")

    assert response.status_code == 200
    assert b"/expenses/add" in response.data


# --------------------------------------------------------------------- #
# Cross-user isolation
# --------------------------------------------------------------------- #

def test_user_a_expense_not_returned_by_get_expenses_by_user_for_user_b(
    logged_in_client, second_user, db_path
):
    """Spec DoD: 'No other user's expenses are ever visible or affected by
    the insert' -- verified directly against the DB helper."""
    from database.db import get_expenses_by_user

    client_a, user_a_id = logged_in_client
    user_b_id = second_user

    client_a.post("/expenses/add", data=VALID_FORM, follow_redirects=False)

    a_expenses = get_expenses_by_user(user_a_id)
    b_expenses = get_expenses_by_user(user_b_id)

    assert len(a_expenses) == 1
    assert len(b_expenses) == 0


def test_user_b_profile_page_never_shows_user_a_expense(
    logged_in_client, second_user, app
):
    """Isolation must also hold end-to-end through the rendered /profile
    page for a second, unrelated logged-in user."""
    client_a, _user_a_id = logged_in_client
    client_a.post("/expenses/add", data=VALID_FORM, follow_redirects=False)

    with app.test_client() as client_b:
        client_b.post(
            "/login",
            data={"email": "other@example.com", "password": "password456"},
            follow_redirects=False,
        )

        response = client_b.get("/profile")

        assert response.status_code == 200
        assert b"Electricity bill" not in response.data
        body = response.data.lower()
        assert b"no expenses" in body or b"empty" in body


def test_second_users_own_expense_does_not_leak_into_first_users_list(
    logged_in_client, second_user, app, db_path
):
    """Symmetric check: an expense added by user B must not show up for
    user A either."""
    client_a, user_a_id = logged_in_client
    user_b_id = second_user

    with app.test_client() as client_b:
        client_b.post(
            "/login",
            data={"email": "other@example.com", "password": "password456"},
            follow_redirects=False,
        )
        client_b.post(
            "/expenses/add",
            data=dict(VALID_FORM, description="User B's private expense"),
            follow_redirects=False,
        )

    response = client_a.get("/profile")

    assert response.status_code == 200
    assert b"User B" not in response.data

    a_rows = _fetch_expense_rows(db_path, user_a_id)
    assert len(a_rows) == 0
