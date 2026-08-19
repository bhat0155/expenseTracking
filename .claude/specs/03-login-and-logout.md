# Spec: Login and Logout

## Overview
This step makes `POST /login` and `GET /logout` functional, introducing Flask session-based authentication — the piece Step 2 (registration) deliberately deferred. `GET /login` already renders the form (`templates/login.html`); this step wires it to verify a submitted email/password against the hashed `password_hash` stored in `users`, and starts a session on success. `GET /logout` clears that session. Together these complete the auth loop: register → log in → (eventually) log out.

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `users` table) — complete.
- Step 2 — Registration (`create_user()`, hashed passwords in `users.password_hash`) — complete.

## Routes
- `POST /login` — validate credentials against the stored password hash, start session, redirect to `/` — public
- `GET /logout` — clear the session, redirect to `/` — public (safe to call whether or not a session currently exists)

`GET /login` is already implemented and unchanged.

## Database changes
No schema changes. The existing `users` table already stores everything needed (`email`, `password_hash`). A new read helper, `get_user_by_email(email)`, will be added to `database/db.py` — this is a query addition, not a schema change.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — change `<form method="POST" action="/login">` to `action="{{ url_for('login') }}"` (CLAUDE.md forbids hardcoded URLs); the existing `{% if error %}` block already renders whatever `error` is passed, no structural change needed

## Files to change
- `app.py` — implement `POST /login` handling on the existing `login()` view (accept both `GET` and `POST` via `methods=["GET", "POST"]`); implement `GET /logout` to clear the session and redirect; set `app.secret_key` (module-level, right after `app = Flask(__name__)`) since `session` requires it and it isn't currently set anywhere
- `database/db.py` — add a `get_user_by_email(email)` helper; route functions must not contain inline SQL
- `templates/login.html` — fix hardcoded form action

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` lives in the same module already used for `generate_password_hash`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug — verify with `check_password_hash`, never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB access goes through `database/db.py`, never inline SQL in `app.py`
- Use `url_for()` for every internal link/redirect — never hardcode paths
- On invalid credentials (email not found OR password mismatch), show the **same generic error** ("Invalid email or password") and a 401 status — never reveal whether the email exists, to avoid user enumeration
- Validate required fields (`email`, `password`) are non-empty server-side even though the form has `required` attributes
- `GET /logout` must not error when no session exists — `session.pop("user_id", None)` (or equivalent) rather than assuming the key is present
- `app.secret_key` set once at module level; do not scatter session config elsewhere

## Definition of done
- [ ] Logging in with the seeded demo user (`demo@spendly.com` / `demo123`) redirects to `/` and sets a session cookie
- [ ] Logging in with a user registered via Step 2, using their correct password, redirects to `/` and sets a session cookie
- [ ] Logging in with a correct email but wrong password re-renders `login.html` with the generic "Invalid email or password" error and does not set a session cookie
- [ ] Logging in with an email that doesn't exist re-renders `login.html` with the same generic error (not a distinct "user not found" message)
- [ ] Logging in with a missing field re-renders `login.html` with an error instead of crashing
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/`
- [ ] Visiting `/logout` while not logged in does not error and still redirects to `/`
- [ ] `GET /login` still renders the form as before
- [ ] `app.py` contains no raw SQL — all queries live in `database/db.py`
- [ ] `login.html` form posts via `url_for('login')`, not a hardcoded path
- [ ] App starts and runs on port 5001 without errors
