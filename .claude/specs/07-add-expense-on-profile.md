# Spec: Add Expense On Profile

## Overview
Implements Step 7 of the Spendly roadmap: letting a logged-in user manually add an expense. Rather than building a separate `/expenses/add` page, the add-expense form lives directly on the profile page (`profile.html`), right above the existing read-only expense list, so a user can log a new expense and immediately see it appear without navigating away. The `POST /expenses/add` route (currently a placeholder stub returning a raw string) becomes the real handler that inserts the expense and redirects back to `/profile`.

## Depends on
- Step 1 (Database setup) — `expenses` table with `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`, and the `CATEGORIES` constant in `database/db.py`
- Step 3 (Login/Logout) — `session["user_id"]` must be set; adding an expense requires an active session
- Step 4 (Profile page design) — `profile.html` and the `GET /profile` handler already render the user's account details and expense list; this step adds a form above that list

## Routes
- `POST /expenses/add` — reads `amount`, `category`, `date`, `description` from the submitted form, validates them, inserts a new expense row for `session["user_id"]`, then redirects to `GET /profile` — logged-in only (redirect to `GET /login` if `session.get("user_id")` is not set). On validation error, re-renders `profile.html` with an error message and a 400 status (same pattern as the profile edit form), without losing the account details or existing expense list.

The existing `GET /expenses/add` stub is removed — the form is embedded in `profile.html`, so there is no standalone add-expense page to `GET`. `@app.route("/expenses/add", methods=["POST"])` replaces it; a bare `GET /expenses/add` will now correctly 405.

## Database changes
No new tables or columns. One new helper function in `database/db.py`:

- `create_expense(user_id, amount, category, date, description)` — `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`, parameterized, follows the same open/insert/commit/close pattern as `create_user`. No return value needed.

The existing `CATEGORIES` constant in `database/db.py` is reused (imported into `app.py`) to populate the category `<select>` and to validate the submitted category server-side.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — add a new `<section>` between the account-details card and the existing "Your expenses" list containing a form (`method="POST"`, `action="{{ url_for('add_expense') }}"`) with fields: `amount` (number input, `step="0.01"`, `min="0.01"`), `category` (`<select>` populated from `categories` passed by the route, matching `CATEGORIES`), `date` (`type="date"`, defaults via browser to today), `description` (optional text input). Reuses `.form-group` / `.form-input` / `.btn-submit` classes already used by the account-details form. Error/success messages reuse the existing `.auth-error` / `.auth-success` pattern already on the page.

## Files to change
- `app.py` — replace the `GET /expenses/add` stub with a `POST /expenses/add` handler; import `CATEGORIES` and `create_expense` from `database.db`; pass `categories=CATEGORIES` into every `render_profile()` call so the dropdown is always populated
- `database/db.py` — add `create_expense(user_id, amount, category, date, description)`
- `templates/profile.html` — add the add-expense form section
- `CLAUDE.md` — update the `GET /expenses/add` row in "Implemented vs stub routes" to reflect the new `POST /expenses/add` route and its Implemented status

## Files to create
None

## New dependencies
No new dependencies

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with werkzeug (not touched by this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py` — never inline SQL in `app.py`
- Unauthenticated access to `POST /expenses/add` redirects to `/login` via `redirect(url_for('login'))`, matching the existing `/profile` auth pattern
- Server-side validation is mandatory even though HTML5 input types (`number`, `date`) provide client-side hints: `amount` must parse as a positive float, `category` must be one of `CATEGORIES`, `date` and `amount` are required; `description` is optional
- On validation failure, re-render `profile.html` (not a redirect) with a 400 status and an error message, exactly like the existing profile-edit error path, so the user doesn't lose their place
- Only insert the expense for `session["user_id"]` — never trust a user-supplied `user_id` from the form

## Definition of done
- [ ] Visiting `/profile` while logged in shows a new "Add expense" form above the expense list, with a category dropdown populated from `CATEGORIES`
- [ ] Submitting the form with valid amount/category/date/description creates a new row in `expenses` for the logged-in user and the redirected `/profile` page shows it at the top of the expense list
- [ ] Submitting with a missing or non-positive amount re-renders `profile.html` with an error message, a 400 status, and does not insert a row
- [ ] Submitting with a category not in `CATEGORIES` re-renders `profile.html` with an error message, a 400 status, and does not insert a row
- [ ] Submitting `POST /expenses/add` while logged out redirects to `/login` and does not insert a row
- [ ] `GET /expenses/add` returns a 405 (method not allowed) instead of the old placeholder string
- [ ] No other user's expenses are ever affected by the insert
- [ ] All internal links/forms in `profile.html` use `url_for()`, none are hardcoded
- [ ] `pytest` passes with no regressions in existing auth/profile tests (if a `tests/` directory exists by this point)
