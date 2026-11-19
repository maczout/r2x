# r2x: where it stands

The present state of r2x and what is left before it is set down. History is in `docs/log/`,
`docs/history.md` and git. Written on 2026-11-18 from the planning notes kept outside the
repository until then.

Roles as in CLAUDE.md: structural engineering and professional judgement are the owner's,
software engineering the developer's. Items that need the owner are marked **(owner)**.

**Versions.** `main` and the tag `v0.4.0` are 0.4.0. **0.5.0 is on the branch `park`**, not
yet merged or released. The image users pull is `ghcr.io/maczout/r2x:VERSION`; 0.5.0's is not
yet published.

**Plan (decided 2026-10-28, owner):** finish the short list below, release 0.5.0, then set r2x
down. Systematic verification gets a first pass here and is completed in the clone project
(r2c), which is also the route to running fast and reliably.

---

## 1. What 0.5.0 adds (on `park`)

Everything in 0.4.0, plus:

- **Linking:** `r2x setup --response FOLDER` checks the program folder, saves it
  (`%APPDATA%\r2x\config.json`; `R2X_RESPONSE` overrides) and pulls the image if needed. Every
  run mounts the folder read-only at `/opt/response`; `r2k.exe` is checked at setup, on every
  run and in the worker, and another build is refused unless linked with `--allow-unverified`.
  Each job copies only the files Response reads (`.exe`, `.dll`, `.dat`, `.dtd`, `.r2k`). Header
  keys `response-files-sha256` and `response-verified` (format version 1 still). `r2x health`
  names files that differ from the verified folder. The image has no Response.
- **Going back a question:** `<` at a define question (`\<` for a literal `<`).
- **The report's title flag** (`● Solved`, `● Updated`) when it reloads out of sight.
- **One disclaimer** (`src/r2x/notice.py`) in the help, `r2x health`, the session's banner, the
  report's footer and the record header.
- **Documents by reader:** README, `docs/guide.md` (users), `docs/internals.md` (builders),
  `docs/raw-format.md`, `docs/risk-register.md`, `docs/history.md`, `docs/dialogs.md`.
- **Ctrl+C:** at the session's prompt it gives a new prompt; elsewhere it stops with
  `r2x: stopped (Ctrl+C)`.

**Verified** (measured, 2026-11-08): the full suite under Wine on `park`, 307 passed and 7
skipped (four Tier A comparisons and three define cases, waiting for hand captures). Through
the real command line and real Docker in a cloud environment: setup, health, a solve (Newbeam's
23 reference exports at the peak, byte for byte, 7.3 s), define steps and a session. That image
was built on a bootstrapped Ubuntu 24.04 base; the release machine's build is the one
released.

## 2. Next: finishing and releasing 0.5.0

In order:

1. **Wording and the command line** (owner): the disclaimer's wording against the owner's
   professional obligations; a tighter, less verbose command line; whether a define should
   skip fields Response would ignore (it asks Response's fields as they are, by the review of
   2026-10-28). Where each piece of text lives and what tests pin it: `docs/internals.md`, *What
   r2x says, and where*.
2. **Still to try on Windows** (owner): Ctrl+C mid-step after the fix of 2026-11-08 (it has to
   get through `wsl docker run`).
3. **Release 0.5.0** (owner): `docs/internals.md`, *Releasing*.
4. **Interface review** (owner): follow the guide's quick start on a fresh Windows account with
   Response downloaded fresh from hadrianworks.com, and review the command line and report as a
   structural engineer would meet them. This also tells whether today's download is the
   verified build of `r2k.exe`.
5. **Hand captures** (owner): the four Tier A cases (`tests/reference/marshall`, `cm4`,
   `newbeam-axial-shear`, `newbeam-nmv`, each with its recipe) and three short define cases
   (`general`, `section`, `tendons-add`), then compared under Wine.
6. **Set it down:** a *Set down* section at the top of this file: the state, the tag, how to
   resume, and what other projects rely on (`docs/raw-format.md`, format version 1).

**The report and v1.0** (owner, an idea to settle): whether inspection of the report is enough
as a control. What the input screen shows and leaves out: `docs/risk-register.md`, *What the
report leaves out*.

## 3. Decisions in force

The full record is in `docs/history.md`; the ones that most shape further work:

- Users link their own copy of Response; r2x does not bundle it (2026-10-28).
- The image is published on GitHub's registry and pushed from the release machine after it has
  been checked there (2026-11-07).
- Another build of `r2k.exe` is refused unless linked with `--allow-unverified` (2026-11-07).
- First verification pass: the risk register, a few Tier A hand captures aimed at errors the
  engineer cannot see, a small Tier C prototype (`tools/tier_c.py`); no Tier B (2026-11-07).
- Response-2000's terms: deferred until there is a plan for a derivative demonstration
  product (2026-10-28). Response-2000 now lives at hadrianworks.com, which asks that work cite
  Bentz's thesis; the README says so.

## 4. Should, could, won't

**Should:** the three define cases and four Tier A captures (item 5 above).

**Could** (each planned on its own if taken up):

- In define: Materials' Detailed pages and Rebar Details; circular and distributed bar
  patterns; standard and user-defined shapes; shrinkage and thermal strains; a file with
  several sections; a way to give a new section another date.
- The cross-section information box (d, d', steel areas, AASHTO shear strength).
- A report at a stage other than the peak.
- Pinning an `r2k.r2k` template (it would change File > New's defaults; the files hash covers
  it).
- Re-implementing the server, if remote or shared use comes back (code in `src/r2x/server`).
- Tier C beyond the prototype: tendons, other units, a cracking-moment check.

**Won't (this project):**

- Full member response, interaction diagrams and the other more sophisticated analyses; the
  Load Deformation Plot; Mohr's Circles.
- Saving the effective input into the record; parsing exports into a schema; values for a
  define given as options (automation writes the input file).
- Completing systematic verification at scale (the clone project); performance work (speed
  comes from the clone); bundling Response-2000 in the image.
- In define: dialog pictures in the report, `?` help on questions, `save` and `show`.
- A check of whether a record is current; Tier B.

## 5. Watch

- **A new section's layer order:** Response keeps a new section's longitudinal layers in the
  order it made them until it next opens the file. Compare define results by solving, not by
  strict bytes (`compare.py`).
- **Response's own dialogs:** r2x passes on Response's questions and messages; a dialog it does
  not recognise stops the step with its text. Modify re-reads every field at the dialog's
  precision (63.90 becomes 64.00), as in the GUI.
- **Frames** are read from the dialog by the controls' rectangles, never fixed in the
  catalogue.
- **Solve finished** = bottom control curve unchanged for 1 s and Response idle by `/proc`;
  Wine gives no signal.
- **Stages that look alike:** with shear one key often matches several stages; the fallback
  pages from stage 0, which costs a pass.
- **Signed zeros:** Wine and Windows can disagree on the sign of a value that prints as zero.
- **Menu positions:** Copy Chart Data is chosen by position in each chart's right-click menu.
- **The clipboard helper can fail once:** in a run of 25 all-stage captures (2026-11-18, r2c's
  oracle archive) one case stopped at stage 36 of 60 with `'cbget 500d6' -> 'err cbget'` and
  matched its fixture when rerun. One occurrence; a retry in the worker is an option if it
  recurs.
- **PowerShell 5.1** re-encodes text piped between programs, which can break a record from
  `--stdout`. Write a file, or use PowerShell 7.4+.
- **The linked folder:** a user's `rebar.dat` or `shape.dat` that differs from the verified
  folder changes bar and shape lists in define; `r2x health` names them.
- **Builds without registry access** (some cloud environments): Docker Hub and PyPI may be
  unreachable from a build; build and release on the release machine.

## 6. Leftovers

- Whether hadrianworks.com's current download is the verified build of `r2k.exe`. If not,
  every new user meets the refusal and needs `--allow-unverified`, or a second verified build.
- When writing to Bentz about the terms, also ask about the command-line version of Response
  that the manual's text-format section mentions.
- Capture screenshots are not kept in the repository; the case READMEs record what they
  showed.
