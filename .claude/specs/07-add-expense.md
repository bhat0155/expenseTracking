# Spec: Add Expense

## Overview
Implements Step 7 of the Spendly roadmap: letting a logged-in user manually add an expense. The `expenses` table and its DB helpers do not exist in the current codebase (they were removed in a prior revert), so this step (re)introduces the `expenses` table, a `CATEGORIES` constant, and the insert/read helpers alongside the actual add-expense feature. A new standalone `GET /expenses/add` page presents the form; `POST /expenses/add` validates and inserts the expense, then redirects to `/profile`. Because there is currently no way to see an expense after adding it, this step also restores a minimal read-only expense list on `profile.html` so the feature is end-to-end verifiable in the browser.

## Depends on
- Step 1 (Database setup) — `users` table with `id`, `name`, `email`, `password_hash`, `created_at`
- Step 3 (Login/Logout) — `session["user_id"]` must be set; adding an expense requires an active session
- Step 4 (Profile page design) — `profile.html` and `GET /profile` already render the user's account details; this step adds an expense list section to that same page

## Routes
- `GET /expenses/add` — renders the add-expense form (`add_expense.html`) with a category dropdown — logged-in only (redirect to `GET /login` if `session.get("user_id")` is not set)
- `POST /expenses/add` — reads `amount`, `category`, `date`, `description` from the submitted form, validates them, inserts a new expense row for `session["user_id"]`, then redirects to `GET /profile` — logged-in only (same redirect rule as above). On validation error, re-renders `add_expense.html` with an error message and a 400 status.

## Database changes
New table in `database/db.py`:

**`expenses`**

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Foreign key → users.id, not null |
| amount | REAL | Not null |
| category | TEXT | Not null |
| date | TEXT | Not null (YYYY-MM-DD format) |
| description | TEXT | Nullable |
| created_at | TEXT | Default datetime('now') |

New module-level constant:
- `CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]`

New functions in `database/db.py`:
- `create_expense(user_id, amount, category, date, description)` — `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`, parameterized, follows the same open/insert/commit/close pattern as `create_user`. No return value needed.
- `get_expenses_by_user(user_id)` — `SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC`, returns all rows, follows the same pattern as `get_user_by_id`.

`init_db()` must create the `expenses` table with `CREATE TABLE IF NOT EXISTS`, same as `users`. `seed_db()` is unchanged — no sample expenses are seeded; the demo user starts with an empty expense list.

## Templates
- **Create:** `templates/add_expense.html` — extends `base.html`; reuses the `.auth-card` / `.form-group` / `.form-input` / `.btn-submit` classes already established in `login.html`/`register.html`; form fields: `amount` (number input, `step="0.01"`, `min="0.01"`, required), `category` (`<select>` populated from `categories` passed by the route, matching `CATEGORIES`), `date` (`type="date"`, required), `description` (optional text input); error message reuses the existing `.auth-error` pattern; a link back to `/profile` using `url_for('profile')`
- **Modify:** `templates/profile.html` — add a read-only "Your expenses" section below the account-details form, listing each expense's date, category, description, and amount (or an empty-state message if the user has none), plus a link to `/expenses/add` using `url_for('add_expense')`

## Files to change
- `app.py` — replace the `GET /expenses/add` stub with real `GET`/`POST` handlers; import `CATEGORIES`, `create_expense`, and `get_expenses_by_user` from `database.db`; pass `expenses=get_expenses_by_user(user_id)` into `render_profile()` calls
- `database/db.py` — add the `expenses` table to `init_db()`, add the `CATEGORIES` constant, add `create_expense()` and `get_expenses_by_user()`
- `templates/profile.html` — add the read-only expense list section and a link to the add-expense page
- `CLAUDE.md` — update the `GET /expenses/add` row in "Implemented vs stub routes" to reflect the new `GET`/`POST /expenses/add` routes and their Implemented status

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with werkzeug (not touched by this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py` — never inline SQL in `app.py`
- Unauthenticated access to either `/expenses/add` route redirects to `/login` via `redirect(url_for('login'))`, matching the existing `/profile` auth pattern
- Server-side validation is mandatory even though HTML5 input types (`number`, `date`) provide client-side hints: `amount` must parse as a positive float, `category` must be one of `CATEGORIES`, `date` and `amount` are required; `description` is optional
- On validation failure, re-render `add_expense.html` (not a redirect) with a 400 status and an error message so the user doesn't lose their input context
- Only insert the expense for `session["user_id"]` — never trust a user-supplied `user_id` from the form
- `PRAGMA foreign_keys = ON` must remain set on every `get_db()` connection

## Definition of done
- [ ] Visiting `/expenses/add` while logged in shows a form with a category dropdown populated from `CATEGORIES`
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Submitting the form with valid amount/category/date/description creates a new row in `expenses` for the logged-in user and redirects to `/profile`, where the new expense appears at the top of the expense list
- [ ] Submitting with a missing or non-positive amount re-renders `add_expense.html` with an error message and a 400 status, and does not insert a row
- [ ] Submitting with a category not in `CATEGORIES` re-renders `add_expense.html` with an error message and a 400 status, and does not insert a row
- [ ] Submitting `POST /expenses/add` while logged out redirects to `/login` and does not insert a row
- [ ] `/profile` shows an empty-state message when the logged-in user has no expenses
- [ ] No other user's expenses are ever visible or affected by the insert
- [ ] All internal links/forms in `add_expense.html` and `profile.html` use `url_for()`, none are hardcoded
- [ ] `pytest` passes with no regressions in existing auth/profile tests (if a `tests/` directory exists by this point)
