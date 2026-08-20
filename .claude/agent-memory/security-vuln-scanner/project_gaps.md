---
name: project-gaps
description: Known project-wide security gaps in Spendly that are out of scope to fix within a single-feature review — re-flag as "known, not new" rather than as fresh criticals
metadata:
  type: project
---

Gaps identified during the Step 7 review (2026-08-20, commit f320b34) that are **pre-existing / project-wide**, not introduced by any single feature. Re-check they're still true on each review, but treat as "known gap" (not a regression) unless a specific commit clearly worsens them:

- **No CSRF protection anywhere in the app.** Confirmed via `grep -ri csrf app.py requirements.txt` → zero hits. Every state-changing POST route (`/register`, `/login`, `/profile` edit, `/expenses/add`, and future `/expenses/<id>/edit` and `/expenses/<id>/delete`) is exposed to CSRF since auth is cookie-session-only with no token check. Fixing this properly with `flask-wtf` would require a new pip dependency (against CLAUDE.md's "no new pip packages without flagging" rule) — a hand-rolled session-stored token is the in-constraint fix, but it's a cross-cutting change touching every form/route, so it should be raised as its own task/step rather than bundled into a single feature's fix. Recommend surfacing this to the user as a standalone follow-up rather than re-deriving it every review.
- **`app.run(debug=True, port=5001)`** (app.py, last line) — Werkzeug debug mode is on. This is expected for local dev in a teaching project at this stage, and CLAUDE.md doesn't flag it as an issue to fix yet. Only worth raising if a task is explicitly about deployment/production hardening.
- **`app.secret_key = "dev-secret-key-change-in-production"`** hardcoded in app.py:20 — a known placeholder, self-documented as dev-only. Same treatment as debug mode: expected at this stage, don't re-flag as a fresh finding unless the task is about production readiness.

See also [[project-conventions]] for what's already correctly implemented.
