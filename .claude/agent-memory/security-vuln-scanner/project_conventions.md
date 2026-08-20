---
name: project-conventions
description: Established security-relevant conventions in Spendly's app.py/db.py, confirmed correct as of Step 7 review (2026-08-20) — use as baseline to avoid re-flagging non-issues
metadata:
  type: project
---

Confirmed-good patterns in this codebase as of commit f320b34 (Step 7, "add expense on profile page"):

- **Parameterized SQL everywhere**: every query in `database/db.py` uses `?` placeholders. No f-strings/`.format()`/concatenation found in `create_user`, `create_expense`, `get_user_by_email`, `get_user_by_id`, `update_user`, `get_expenses_by_user`, `seed_db`, `init_db`. Do not re-flag parameterized queries as injection risk.
- **`get_db()` always runs `PRAGMA foreign_keys = ON`** (database/db.py:15) — confirmed present on every connection. This is the one required FK-enforcement line per CLAUDE.md; verify it's still there on future reviews since it's easy to accidentally drop when refactoring `get_db()`.
- **Ownership pattern for expenses**: routes that touch expense data always source `user_id` from `session["user_id"]`, never from form/query params. `add_expense` (app.py:142-163) follows this correctly. **Watch for regressions here** — Step 8 (`GET /expenses/<id>/edit`) and Step 9 (`GET /expenses/<id>/delete`) are still stubs; when implemented, the critical check to verify is that the fetched expense's `user_id` matches `session["user_id"]` before allowing edit/delete (classic IDOR risk on a per-`id` resource route). Flag if that ownership check is missing when those stubs are implemented.
- **Jinja2 templates**: no `| safe`, no `Markup()`, no raw HTML concatenation found anywhere in `templates/profile.html` (or elsewhere, based on this review). All expense fields (`description`, `category`, `date`, `amount`) rendered via plain `{{ }}` which autoescapes. Do not flag `{{ }}` output as XSS.
- **Redirects**: all `redirect(url_for(...))` calls use hardcoded internal endpoint names, no user-controlled `next` param anywhere yet. No open-redirect surface currently exists.
- **Error pattern for validation failures**: routes re-render the relevant template with `error=...` and an explicit `400` status (e.g. `return render_profile(user_id, error="..."), 400`), rather than bare string returns. This is the established, acceptable pattern for form-validation errors in this project (distinct from `abort()`, which CLAUDE.md reserves more for true HTTP errors like 404/403). Do not flag this pattern as a violation.

See also [[project-gaps]] for known unresolved issues (CSRF, debug mode) that are project-wide and out of scope for single-feature fixes.
