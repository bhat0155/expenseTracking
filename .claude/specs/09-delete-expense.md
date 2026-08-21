# Spec: Delete Expense

## Overview
This feature lets a logged-in user delete an expense they own. It replaces the current `GET /expenses/<id>/delete` stub with a real GET/POST route: GET renders a confirmation page showing the expense's details, and POST performs the deletion and redirects back to `/profile`. It follows the same ownership-check and 404 pattern established in Step 8 (Edit Expense), and is the final CRUD operation needed to complete basic expense management in Spendly.

## Depends on
- Step 1 — Database setup (`users`, `expenses` tables)
- Step 3 — Login and Logout (session-based auth)
- Step 7 — Add Expense (`CATEGORIES`, expense row rendering conventions)
- Step 8 — Edit Expense (`get_expense_by_id`, ownership-check pattern, `edit_expense.html` layout to mirror)

## Routes
- `GET /expenses/<int:id>/delete` — render a confirmation page showing the expense to be deleted — logged-in, owner only
- `POST /expenses/<int:id>/delete` — delete the expense, redirect to `/profile` — logged-in, owner only

Both methods are handled by a single `delete_expense(id)` view, replacing the current stub.

Access rules:
- If no user is logged in, redirect to `/login` (matches `edit_expense`, `add_expense`, `profile`).
- If the expense does not exist, `abort(404)`.
- If the expense exists but does not belong to the current user, `abort(404)` (do not leak existence via 403).

## Database changes
No new tables or columns. `database/db.py` needs one new function (verified by reading the file — not present today):
- `delete_expense(expense_id)` — parameterized `DELETE FROM expenses WHERE id = ?`

Ownership is enforced in the route (compare `expense["user_id"]` to `session["user_id"]`) using the existing `get_expense_by_id`, consistent with `edit_expense`.

## Templates
- **Create:** `templates/delete_expense.html` — same `auth-section` / `auth-container` structure as `edit_expense.html`, displaying the expense's date, category, description, and amount as read-only summary text, with a confirmation message (e.g. "Are you sure you want to delete this expense?"). Contains a `<form method="POST" action="{{ url_for('delete_expense', id=expense['id']) }}">` with a submit button labeled "Delete expense", plus a "Cancel" link back to `url_for('profile')`.
- **Modify:** `templates/profile.html` — add a "Delete" link/button next to the existing "Edit" link in each expense row, pointing to `url_for('delete_expense', id=expense['id'])`.

## Files to change
- `app.py` — replace the `delete_expense` stub with the real GET/POST implementation
- `database/db.py` — add `delete_expense`
- `templates/profile.html` — add the delete link to each expense row
- `CLAUDE.md` — update the routes table to mark `GET /expenses/<id>/delete` and `POST /expenses/<id>/delete` as Implemented

## Files to create
- `templates/delete_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a to this feature, but no regression to existing auth code)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic only in `database/db.py`, never inline in `app.py`
- Ownership check must 404, not redirect, when a user tries to delete another user's expense
- Deletion must only happen on POST — GET must never mutate data

## Definition of done
- [ ] Logged out, visiting `/expenses/1/delete` redirects to `/login`
- [ ] Logged in as the owner, `GET /expenses/<id>/delete` renders a confirmation page showing that expense's date, category, description, and amount
- [ ] Logged in as a different user, `GET /expenses/<id>/delete` for someone else's expense returns 404
- [ ] Visiting `/expenses/999999/delete` (nonexistent id) returns 404
- [ ] Submitting `POST /expenses/<id>/delete` as the owner removes the row from SQLite and redirects to `/profile`, where the expense no longer appears
- [ ] Submitting `POST /expenses/<id>/delete` for an expense owned by another user returns 404 and does not delete the row
- [ ] `profile.html`'s expense list shows a working delete link for each expense
