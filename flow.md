# Spec-driven feature workflow

A repeatable sequence for building a feature step with Claude Code: spec first,
plan second, code third. Works on any project — swap in your own conventions
file and spec template.

## Prerequisites (one-time setup per project)

- A `CLAUDE.md` (or similar) at the repo root describing conventions,
  architecture, and — if the project is built incrementally — a roadmap of
  steps/routes/features with their status (done / stub / not started).
- A `/create-spec` slash command (e.g. `.claude/commands/create-spec.md`) that
  knows how to turn "step number + feature name" into a spec document. It
  should at minimum: verify a clean working tree, create a feature branch,
  research the existing codebase, and write a spec file using a fixed
  template (Overview, Routes, DB/schema changes, Files to change/create,
  Rules, Definition of Done).

## The flow

1. **Run the slash command with a step number and feature name.**
   Example: `/create-spec 03 login-and-logout`.

2. **The command creates the spec.** Under the hood it:
   - checks the working directory is clean (stops and asks you to
     commit/stash if not)
   - derives a branch name from the feature name (`feature/<slug>`),
     bumping it (`-01`, `-02`, ...) if already taken
   - switches to the main branch and pulls latest
   - creates and checks out the new feature branch
   - reads the conventions file, the main entry point(s), the data layer,
     and any existing specs, so the new spec doesn't duplicate or contradict
     prior work
   - confirms the requested step isn't already marked complete
   - writes the spec to a predictable path (e.g. `.claude/specs/<step>-<slug>.md`)

3. **Review the spec file yourself.** Read it before doing anything else —
   this is the cheapest point to catch a wrong assumption, since nothing has
   been implemented yet.

4. **Enter Plan Mode** (Shift+Tab twice) and point Claude at the spec:
   *"Read `.claude/specs/<step>-<slug>.md` and create a detailed
   implementation plan. Don't write any code."*
   Claude will:
   - explore the codebase further (existing patterns, related files,
     anything the spec didn't fully pin down)
   - surface any ambiguous design decisions as questions instead of
     guessing (e.g. "where should this redirect to?")
   - write a concrete, file-by-file implementation plan and ask for approval

5. **Approve the plan.** Once approved, Claude exits plan mode and
   implements it — editing the exact files named in the plan, in the order
   specified, following the conventions file's rules throughout.

6. **Verify the change.** Run the app (or test suite) and confirm the
   spec's "Definition of Done" checklist actually holds against live
   behavior, not just against the diff. Fix anything that doesn't check out.

7. **Course-correct if needed.** If something about the implemented behavior
   isn't what you wanted (e.g. "redirect to login, not the dashboard"),
   say so directly — Claude adjusts the code and, importantly, updates the
   spec file too, so it stays an accurate record of what was actually built.

8. **Commit and push the feature branch.**

9. **Merge into main** (PR review, or direct merge, per your project's norm).

10. **Sync up:** switch back to main, pull, and delete the feature branch
    (locally and on the remote) now that it's merged.

11. **Repeat from step 1** for the next step/feature, incrementing the step
    number.

## Why this order matters

- Spec before plan before code means design mistakes get caught in a text
  document, not in a diff. Each stage is cheaper to fix than the next.
- Deriving the branch name and spec path from the step number keeps a
  1:1 mapping between roadmap steps, branches, and spec files — you can
  always find the spec that justifies a given piece of code.
- Updating the spec when behavior changes (step 7) keeps `.claude/specs/`
  trustworthy as documentation, instead of drifting from reality over time.
