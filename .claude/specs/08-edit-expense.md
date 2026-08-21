# Spec: Edit Expense

## Overview
This feature lets a logged-in user edit an existing expense they own. It replaces the current `GET /expenses/<id>/edit` stub with a real GET/POST route that pre-fills a form with the expense's current values, validates submitted changes the same way `add_expense` does, and persists the update. It follows directly from Step 7 (Add Expense), reusing the same validation rules and form layout, and sets up the pattern Step 9 (Delete Expense) will also need for ownership checks.

## Depends on
- Step 1 — Database setup (`users`, `expenses` tables)
- Step 3 — Login and Logout (session-based auth)
- Step 7 — Add Expense (`CATEGORIES`, `create_expense` pattern, `add_expense.html` layout to mirror)

## Routes
- `GET /expenses/<int:id>/edit` — render a pre-filled edit form for the expense — logged-in, owner only
- `POST /expenses/<int:id>/edit` — validate and update the expense, redirect to `/profile` — logged-in, owner only

Both methods are handled by a single `edit_expense(id)` view, replacing the current stub.

Access rules:
- If no user is logged in, redirect to `/login` (matches `add_expense`, `profile`).
- If the expense does not exist, `abort(404)`.
- If the expense exists but does not belong to the current user, `abort(404)` (do not leak existence via 403).

## Database changes
No new tables or columns. `database/db.py` needs two new functions (none of this exists today — verified by reading the file):
- `get_expense_by_id(expense_id)` — `SELECT * FROM expenses WHERE id = ?`, returns one row or `None`
- `update_expense(expense_id, amount, category, date, description)` — parameterized `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ?`

Ownership is enforced in the route (compare `expense["user_id"]` to `session["user_id"]`), not in the DB layer, consistent with how `update_user` works today.

## Templates
- **Create:** `templates/edit_expense.html` — same `auth-section` / `auth-container` / `form-group` structure as `add_expense.html`, with inputs pre-filled from the existing expense (`value="{{ expense['amount'] }}"`, `selected` on the matching category option, `value="{{ expense['date'] }}"`, `value="{{ expense['description'] or '' }}"`). Submit button reads "Save changes". Form posts to `url_for('edit_expense', id=expense['id'])`.
- **Modify:** `templates/profile.html` — point each expense row's existing edit link/button at `url_for('edit_expense', id=expense['id'])` instead of a dead/placeholder link (only if not already wired this way — verify before changing).

## Files to change
- `app.py` — replace the `edit_expense` stub with the real GET/POST implementation
- `database/db.py` — add `get_expense_by_id` and `update_expense`
- `templates/profile.html` — ensure edit links point to the new route (only if needed)
- `CLAUDE.md` — update the routes table to mark `GET /expenses/<id>/edit` and `POST /expenses/<id>/edit` as Implemented

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a to this feature, but no regression to existing auth code)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Reuse the exact validation rules from `add_expense` (amount is a positive float, category in `CATEGORIES`, date required)
- DB logic only in `database/db.py`, never inline in `app.py`
- Ownership check must 404, not redirect, when a user tries to edit another user's expense

## Definition of done
- [ ] Logged out, visiting `/expenses/1/edit` redirects to `/login`
- [ ] Logged in as the owner, `GET /expenses/<id>/edit` renders a form pre-filled with that expense's amount, category, date, and description
- [ ] Logged in as a different user, `GET /expenses/<id>/edit` for someone else's expense returns 404
- [ ] Visiting `/expenses/999999/edit` (nonexistent id) returns 404
- [ ] Submitting valid changes via `POST /expenses/<id>/edit` updates the row in SQLite and redirects to `/profile`, where the updated values are visible
- [ ] Submitting an invalid amount (blank, 0, negative, non-numeric) or missing category/date re-renders `edit_expense.html` with a 400 status and an error message, without touching the database
- [ ] `profile.html`'s expense list links to the correct edit URL for each expense
