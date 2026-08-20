---
name: frontend-ui
description: >-
  Build clean, consistent frontend UI for Spendly that matches the existing
  design system instead of inventing new patterns. Use whenever creating or
  modifying a template (.html), adding/changing page styling, designing a new
  page or feature UI, building a form, or asked to make something "look nice,"
  "clean up the UI," or "match the design." Covers Jinja2 templates under
  templates/, the single stylesheet static/css/style.css, and static/js/main.js.
---

# Spendly Frontend UI

Spendly has one small, deliberate design system: a handful of CSS variables, a
short list of reusable component classes, and two fonts. The job of this
skill is to make new UI look like it was built by the same person who built
`login.html` — not to introduce a new visual language.

## Before writing any markup or CSS

Read, in this order:
1. `static/css/style.css` — full file. Note the `:root` variables and the
   existing component classes (see cheat sheet below). Every section is
   marked with a `/* ---- */` comment header — match that convention.
2. `templates/base.html` — the blocks available (`title`, `head`, `content`,
   `scripts`), the nav bar's logged-in/logged-out conditional, and the
   footer. Every new template extends this.
3. The closest existing template to what you're building (`login.html`/
   `register.html` for forms and centered cards, `landing.html` for
   marketing/stat/feature layouts, `profile.html` for account/list pages).
   Copy its structure, don't reinvent it.

## Reuse before you invent

Check this list before writing a new CSS rule — most UI needs are already
covered:

- **Auth/centered-form pages:** `.auth-section` → `.auth-container` (440px
  max-width) → `.auth-header` (`.auth-title` + `.auth-subtitle`) → form
- **Forms:** `.form-group`, `.form-input` (has a `:focus` state already)
- **Buttons:** `.btn-submit` (full-width, for forms), `.btn-primary`
  (inline CTA), `.btn-ghost` (secondary/outline)
- **Feedback banners:** `.auth-error`, `.auth-success`
- **Cards/stats/lists:** `.mock-card`, `.mock-stat` (landing page stat
  tiles), `.expense-list`/`.expense-row` (row-style list with a leading
  icon — see `profile.html` for the pattern)
- **Nav/footer:** already wired in `base.html`, don't touch unless the task
  requires a new nav item

Only add a new class when nothing above fits.

**Where new CSS goes — known inconsistency, read before choosing:**
`CLAUDE.md`'s documented convention is "page-specific styles → new `.css`
file, not inline `<style>` tags," loaded via that template's
`{% block head %}`. In practice, every page built so far (login, register,
profile) ignored that and added its rules straight into the single
`static/css/style.css`, under a new `/* ---- */` section near the related
existing section. Follow the documented convention (a dedicated
`static/css/<page>.css`) for genuinely new, unrelated pages unless the user
says otherwise — but if you're extending an existing auth/profile-style
page, matching the file it's already in beats splitting styles across files
mid-page. When in doubt, ask.

## Rules (from CLAUDE.md, non-negotiable)

- CSS variables only — never a hardcoded hex value. Use the existing
  `--ink*`, `--paper*`, `--accent*`, `--danger*`, `--border*`, `--radius-*`,
  `--font-*` variables. If a genuinely new color/spacing value is needed,
  add it to `:root` rather than hardcoding it inline.
- Every template extends `base.html`.
- Every internal link/asset uses `url_for()` — never a hardcoded path.
- Vanilla JS only, and only if the interaction truly needs it — most pages
  in this app (including forms) work fine with a plain POST + re-render, no
  JS required. If JS is needed, it goes in `static/js/main.js` or a
  `{% block scripts %}`, never inline `<script>` logic beyond wiring.
- No inline `<style>` tags — CSS lives in `style.css`.
- No new pip/npm packages, no CSS/JS frameworks, no build step.

## Visual language cheat sheet

- Headings/display text → `var(--font-display)` (DM Serif Display). Body
  text, labels, buttons → `var(--font-body)` (DM Sans).
- Radius scale: `--radius-sm` (6px, inputs/buttons) · `--radius-md` (12px,
  cards) · `--radius-lg` (20px, hero/mock visuals).
- Color roles: `--ink` (primary text/buttons), `--ink-muted`/`--ink-faint`
  (secondary text), `--paper`/`--paper-warm` (page backgrounds),
  `--paper-card` (card/input backgrounds), `--accent` (green, primary
  action/hover), `--accent-2` (gold, secondary/positive accent),
  `--danger` (errors). Each has a matching `-light` variant for subtle
  backgrounds (e.g. `--danger-light` behind `.auth-error`).
- Keep it plain: no shadows beyond what's already used (`.mock-card`'s
  subtle box-shadow), no gradients, no animation beyond the existing
  `transition: ... 0.2s` hover states.

## Responsive

There's a `/* Responsive */` section at the bottom of `style.css` with
breakpoints at `900px` and `600px`. If new UI can break on narrow screens
(grids, wide tables/rows, side-by-side layouts), add rules there rather than
scattering media queries throughout the file.

## Before finishing

Compare the new template/CSS against an existing page side by side (or in
the browser if available) — spacing, font pairing, button styles, and error/
success banner treatment should be indistinguishable from the rest of the
app. If something looks like it belongs to a different app, it's probably
using a pattern that isn't in the cheat sheet above — go find the existing
equivalent instead of keeping the new one.
