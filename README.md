# Spendly

A lightweight personal expense tracker built with Flask and SQLite. Spendly is a
teaching project (post-MADD course), built step-by-step — but the real point of
this repo is **how it was built**: entirely through Claude Code, using a
project-specific setup of custom commands, subagents, a skill, and MCP servers
instead of one long unstructured chat.

## Stack

- Flask (no blueprints — all routes in `app.py`)
- SQLite (no ORM, parameterized queries only)
- Vanilla JS / plain Jinja2 templates (no frontend framework)

## Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python app.py                     # runs on http://localhost:5001
pytest                            # run the test suite
```

---

## How this app is built with Claude Code

Everything below lives in `.claude/` and `CLAUDE.md`, and is checked into the
repo so the workflow is reproducible, not just something that happened once in
a chat window.

### `CLAUDE.md` — the project's operating manual

The single source of truth Claude reads on every session: architecture rules
(where routes/DB logic/templates belong), code style, tech constraints (Flask
+ SQLite + vanilla JS only, no new packages without flagging it), the roadmap
table of implemented-vs-stub routes, and a **subagent policy** that Claude
must follow, e.g.:
- always explore the codebase with a subagent before implementing a new feature
- always verify test results with a subagent after implementing
- always use the Plan subagent when in plan mode

This means Claude isn't just told rules once — it re-reads them at the start
of every task and applies them mechanically.

### Custom slash commands (`.claude/commands/`)

| Command | What it does |
|---|---|
| `/create-spec <feature>` | Checks the working tree is clean, creates a feature branch, researches the codebase, and writes a structured spec (`.claude/specs/NN-feature.md`) covering routes, DB changes, templates, and a testable Definition of Done — *before* any code is written |
| `/test-feature <spec-name>` | Runs a two-step pipeline: the `spendly-test-writer` subagent writes tests from the spec, then the `security-vuln-scanner` subagent runs them and classifies any failure as a real bug, a missing feature, or a bad test — without fixing anything itself |
| `/seed-user` | Generates and inserts one realistic dummy user directly into the DB, following the schema in `database/db.py` |
| `/seed-expense <user_id> <count> <months>` | Bulk-inserts realistic categorized expenses for a given user, spread across a date range, in a single transaction |

Every feature in this app (registration, login/logout, profile, add-expense)
started as a `/create-spec` run and ended with a `/test-feature` run.

### Custom subagents (`.claude/agents/`)

- **`spendly-test-writer`** — writes pytest tests from the *spec*, not the
  implementation, so tests catch bugs instead of encoding them. Refuses to
  write full tests for stub routes, and reports any bug it notices instead of
  quietly fixing it.
- **`security-vuln-scanner`** — reviews new/changed code for SQL injection,
  IDOR, XSS, CSRF, weak auth, and info-leaks, scoped to this project's Flask +
  SQLite constraints. Keeps project-scoped memory (`.claude/agent-memory/`) of
  recurring issues and conventions across reviews.

Both are invoked automatically by `/test-feature`, and proactively by Claude
whenever CLAUDE.md's subagent policy calls for them (e.g. after implementing
a route).

### Skill (`.claude/skills/frontend-ui/`)

A reusable skill Claude loads whenever it touches a template or CSS. It
enforces "look like the same person built every page" — reuse existing CSS
variables and component classes (`.auth-card`, `.form-input`, `.btn-submit`,
...) before inventing new ones, extend `base.html`, never hardcode a URL or a
hex color.

### Plan mode

Non-trivial features go through Claude's plan mode: an `Explore` subagent
researches the relevant code, a `Plan` subagent drafts the implementation
approach, and the plan is written to a plan file and approved *before* any
edit happens. The Add Expense feature (`.claude/specs/07-add-expense.md`) is
a full example of this: spec → plan mode → implementation → generated tests →
subagent-run verification → a real bug caught (NaN bypassing amount
validation) → fix → re-verify → commit.

### MCP servers

- **sqlite** — direct read/inspect access to the local `expense_tracker.db`
  during development and debugging
- **github** — PRs, commits, and repo metadata without leaving the session
- **figma** — pulling design context when translating a design into a
  template

---

## Roadmap

See the "Implemented vs stub routes" table in `CLAUDE.md` for what's live and
what's still a stub. Specs for each completed step live in `.claude/specs/`.
