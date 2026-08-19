# Spec: Registration

## Overview
This step makes `POST /register` functional so a visitor can actually create a Spendly account. `GET /register` already renders the form (`templates/register.html`); this step wires that form to `database/db.py`, validates and hashes the submitted password, and inserts a new row into `users`. Registration does not log the user in — after creating the account, they're redirected to `/login` to sign in with their new credentials. It builds directly on the database layer from Step 1; session handling is deferred to whichever step implements login.

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `users` table) — complete.

## Routes
- `POST /register` — validate form input, hash password, insert user, redirect to `/login` — public

`GET /register` is already implemented and unchanged.

## Database changes
No database changes. The existing `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already supports registration. Uniqueness is enforced by the existing `email UNIQUE NOT NULL` constraint — rely on it, do not add a pre-check query that could race.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — change `<form method="POST" action="/register">` to `action="{{ url_for('register') }}"` (CLAUDE.md forbids hardcoded URLs); render `{{ error }}` when registration fails (already scaffolded, no structural change needed)

## Files to change
- `app.py` — implement `POST /register` handling on the existing `register()` view (accept both `GET` and `POST` via `methods=["GET", "POST"]`)
- `database/db.py` — add a `create_user(name, email, password_hash)` helper; route functions must not contain inline SQL
- `templates/register.html` — fix hardcoded form action

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` is already used in `database/db.py`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`, never store plaintext)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB access goes through `database/db.py`, never inline SQL in `app.py`
- Use `url_for()` for every internal link/redirect — never hardcode paths
- On duplicate email, catch `sqlite3.IntegrityError` and re-render `register.html` with a friendly `error` message and a 400 status — do not let the exception crash the request
- Validate required fields (`name`, `email`, `password`) are non-empty server-side even though the form has `required` attributes, since client-side validation can be bypassed
- Registration does not start a session — the user must log in separately after their account is created

## Definition of done
- [ ] Submitting the register form with a new name/email/password creates a row in `users` with a hashed (not plaintext) password
- [ ] After successful registration, the user is redirected to `/login`
- [ ] Submitting with an email that already exists re-renders `register.html` with an error message and does not create a duplicate row
- [ ] Submitting with a missing field re-renders `register.html` with an error instead of crashing
- [ ] `GET /register` still renders the form as before
- [ ] `app.py` contains no raw SQL — all queries live in `database/db.py`
- [ ] `register.html` form posts via `url_for('register')`, not a hardcoded path
- [ ] App starts and runs on port 5001 without errors
