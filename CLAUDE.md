# Working on r2x

r2x runs Response-2000 from the command line: it drives Response under Wine in a container,
records what Response gives, and builds sections through Response's own dialogs. This file is
how work on r2x is done, by a person or a coding agent. It is short on purpose: read it whole,
then read selectively.

## Roles

- **The owner** is the structural engineer responsible for r2x. Structural engineering and
  professional judgement are the owner's: scope, what users are told, the disclaimer, whether
  a result can be relied on.
- **The developer** (a person or a coding agent) does the software engineering.

"Engineering" in this repository means structural engineering unless it says otherwise. Mark
anything that needs a structural or professional judgement as such and leave it to the owner.

## Instruction hierarchy

When these pull against each other, the higher one wins.

1. **The owner's decisions.** Up to 0.5.0 they are in `docs/history.md`; since then, in the
   session logs (`docs/log/`) and summarised in `docs/status.md`. Where they are silent, the
   developer decides and records the decision.
2. **Response-2000 is the reference.** r2x reports Response's own results, unchanged. Agreement
   means the same bytes as Response gives on Windows (the hand-captured cases in
   `tests/reference/`), not a tolerance. A difference that cannot be removed is a finding for
   the owner, recorded in `docs/risk-register.md`, never smoothed over.
3. **r2x stays thin.** It drives Response and records what it gives: no analysis of its own,
   no parsing into a schema, no performance work. Those belong to other projects (`docs/status.md`,
   *Won't*).
4. **The tests** guard what works. Rerun the Wine tests on any change to Wine, the image or
   the worker.

r2x is being set down after 0.5.0: work outside the list in `docs/status.md` needs the
owner's say-so.

When a goal and a constraint conflict and this list does not settle it, stop that line of
work, record the question under "Open questions for the owner" in the session log, and carry
on with something else.

## Starting a session

Read this file, `docs/status.md`, and the latest file in `docs/log/`. Read anything else only
when the work needs it (`docs/internals.md` before changing the worker, the client or the
image; `docs/guide.md` before changing anything a user sees). Run `python tools/check.py`.

A development environment: `docs/internals.md`, *Running without Docker* and *Tests*.
Response-2000's program folder is the user's own and is never committed; tests find it
through `R2X_RESPONSE_DIR`.

## During a session

- **Commit as you go.** Small commits, each with its reason in the message. Push the working
  branch at least at every natural stopping point: a working environment can disappear, and
  only what is pushed survives.
- **A script that answered a question goes in `tools/` in the same session**, with a
  docstring saying what it answers. Nothing useful stays in a scratch folder.
- **Data stays out of the repository**: Response-2000 and its files, screenshots, and full
  captures. Reference exports in `tests/reference/` are the exception: they are the oracle.
- **Mark where every claim comes from.** Numbers are *measured* (and how: command, machine),
  *estimated* (and from what), or *inferred*. The owner's decisions are marked as the owner's,
  with the date; the developer's readings of them are marked "reading, for the owner to
  confirm".
- **What a user sees has one source.** The disclaimer is in `src/r2x/notice.py`; where each
  piece of text lives is in `docs/internals.md`, *What r2x says, and where*. Change it there,
  and keep `docs/guide.md` in step (tests check the help text against it).

## Ending a session

1. Write `docs/log/YYYY-MM-DD-NN.md` from `docs/log/TEMPLATE.md`. Keep it short. The sections
   that matter most: what was tried and dropped (so it is not tried again) and the decisions
   made, each with who made it and why.
2. Update `docs/status.md` to what is true now. It is a description of the present, not a
   history; the history is in the logs, `docs/history.md` and git.
3. `pytest` and `python tools/check.py` pass; say in the log whether the Wine suite was run.
   Push.

Releases (tags and the published image) are the owner's: `docs/internals.md`, *Releasing*.

Not wanted: a changelog, a commit log, or recording commit IDs in files. Git keeps those.

## Where things are

| What | Where |
|---|---|
| Present state, open items, decisions in force | `docs/status.md` |
| What happened in each session | `docs/log/` |
| Decisions and findings up to 0.5.0 | `docs/history.md` |
| For users | `README.md`, `docs/guide.md` |
| For builders: how it works, tests, releasing | `docs/internals.md` |
| The record format | `docs/raw-format.md` |
| Response's dialogs, as define asks them | `docs/dialogs.md` |
| Where r2x could differ from Response | `docs/risk-register.md` |
| Checks before pushing | `pytest`, `tools/check.py` |
