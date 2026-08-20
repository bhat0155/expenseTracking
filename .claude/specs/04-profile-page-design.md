# Spec: Profile Page Design

## Overview
Implements the `/profile` route (currently a stub returning a raw string) as a real page where a logged-in user can view their account details — name, email, and member-since date — update their name and email, and see a read-only list of their expenses. This is Step 4 of the Spendly roadmap, sitting between auth (Step 3: login/logout) and expense management (Step 7+). The expense list here is read-only (no add/edit/delete) — those remain Step 7-9 stubs untouched by this change.

## Depends on
- Step 1 (Database setup) — `users` table with `id`, `name`, `email`, `password_hash`, `created_at`
- Step 2 (Registration) — users must be able to register before they have a profile to view
- Step 3 (Login/Logout) — `session["user_id"]` must be set on login; profile access requires an active session

## Routes
- `GET /profile` — displays the current user's name, email, and member-since date, plus an edit form pre-filled with their name/email — logged-in only (redirect to `GET /login` if `session.get("user_id")` is not set)
- `POST /profile` — updates the current user's name and email, re-renders `profile.html` with a success or error message — logged-in only (same redirect rule as above)

## Database changes
No new tables or columns. Three new helper functions in `database/db.py`:

- `get_user_by_id(user_id)` — `SELECT * FROM users WHERE id = ?`, returns a single row or `None`
- `update_user(user_id, name, email)` — `UPDATE users SET name = ?, email = ? WHERE id = ?`, parameterized, no return value needed
- `get_expenses_by_user(user_id)` — `SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC`, returns all rows (read-only, no new writes to `expenses`)

All follow the existing pattern used by `get_user_by_email` and `create_user` (open connection via `get_db()`, close before returning).

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; reuses the `.auth-card` / `.form-group` / `.form-input` / `.btn-primary` classes already established in `login.html` and `register.html` for the account-details card; adds a wider `.expense-section` below it with a plain HTML table (date, category, description, amount) listing the user's expenses, or an empty-state message if they have none
- **Modify:** none — `base.html` already links to `/profile` in the logged-in nav state; no changes needed there

## Files to change
- `app.py` — replace the `/profile` stub with a real `GET`/`POST` handler
- `database/db.py` — add `get_user_by_id(user_id)`, `update_user(user_id, name, email)`, and `get_expenses_by_user(user_id)`

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- Passwords are out of scope for this step — do not add password-change logic here
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py` — never inline SQL in `app.py`
- Unauthenticated access to `/profile` redirects to `/login` via `redirect(url_for('login'))` — do not use `abort()` for this case, since it's a navigation flow, not an error
- Duplicate-email conflicts on update should re-render `profile.html` with an error message and a 400 status, matching the existing register/login error pattern (check via `get_user_by_email` before updating, excluding the current user's own row)

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Visiting `/profile` while logged in renders `profile.html` showing the correct name, email, and member-since date for the session's user
- [ ] Submitting the edit form with a new name and email updates the `users` row and the page reflects the new values after re-render
- [ ] Submitting the edit form with an email already used by another account shows an error and does not change the database
- [ ] `/profile` lists all of the logged-in user's expenses (date, category, description, amount), or an empty-state message if they have none — no other user's expenses ever appear
- [ ] All internal links in `profile.html` use `url_for()`, none are hardcoded
- [ ] `pytest` passes with no regressions in existing auth tests (if a `tests/` directory exists by this point)
