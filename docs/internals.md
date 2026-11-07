# r2x internals

For whoever builds on r2x or changes it. Using it is in `docs/guide.md`; the record's layout,
r2x's contract with whatever reads it, is in `docs/raw-format.md`. Why things are as they are,
and what was found in Response along the way, is in `docs/history.md`.

## The parts

```
r2x (Windows)  ──wsl docker run──▶  container: Xvfb + Wine + helper.exe + the worker
                                     └── /opt/response: the user's Response-2000, read-only
```

- **The command line** (`src/r2x/cli.py`, `define.py`, `shell.py`, `config.py`): standard
  library only. It links the user's Response folder (`r2x setup`), builds one `docker run` per
  input or define step, shows progress and asks the questions. On Windows it runs docker in WSL
  (`wsl --exec docker`) and maps paths to `/mnt/c/...`.
- **The image** (`Dockerfile`): Ubuntu 24.04, Wine pinned to `9.0~repack-4build3`, Xvfb, the
  helper, r2x, and a 32-bit Wine prefix made at build time. No Response: each run mounts the
  user's program folder read-only at `/opt/response`. Published as
  `ghcr.io/maczout/r2x:VERSION`; the client runs the image of its own version.
- **The worker** (`src/r2x/worker/`), in the container: starts Response from a fresh copy of
  its program files on its own virtual display, drives it through the helper, and writes the
  record (and the report) to the mounted output folder.
- **The helper** (`src/r2x/worker/helper.c`): a small Win32 program in the same Wine prefix as
  Response, answering one command per line on stdin: list windows and controls, post and send
  messages, read the clipboard as raw CF_TEXT bytes, snap a window's picture.

## Response's program folder

`src/r2x/response.py`, shared by the command line and the worker:

- **Verified builds:** `VERIFIED_EXE`, SHA-256 of `r2k.exe` (1.9.7). The command line checks
  the folder at `r2x setup` and before every run; the worker checks it again in the container.
  Another build runs only with `R2X_ALLOW_UNVERIFIED=1`, which the command line passes
  (`docker run -e`) when setup was given `--allow-unverified`.
- **Program files:** the files with the suffixes Response reads (`.exe`, `.dll`, `.dat`,
  `.dtd`, `.r2k`). Each job copies only these into its own folder, so a linked folder's
  `Response.ini` (Response's recent-files list, rewritten by every session on Windows) and the
  sections people keep there neither reach Response nor change the hash. Response ran the full
  Wine suite from such a copy on 2026-11-07.
- **The files hash** (`response-files-sha256` in the record): SHA-256 of the lines `HASH  name`
  that `sha256sum` prints for the program files, sorted by name with case ignored, each ending
  in a line feed. `VERIFIED_FILES` holds the verified folder's, so `r2x health` can name a
  user's `rebar.dat` or `shape.dat` that differs.
- **The setting:** `r2x/config.py`, `%APPDATA%\r2x\config.json` (or `~/.config/r2x/`;
  `R2X_CONFIG` overrides). `R2X_RESPONSE` overrides the folder.

## How a solve works

- `runner.py` starts Xvfb on a free display, checks the Wine prefix (`prefix.py`), copies the
  program files into a job folder and starts `r2k.exe` with the input. Every container has its
  own display and prefix, so several run at once (`--parallel`): Response's exports travel
  through the clipboard, which belongs to one wineserver and one display.
- `dialogs.py` applies `--units`, `--factors`, `--initial` and `--increment` through
  Preferences (menu command 321) and Define Loading (152), units before loads, and reads the
  settings in effect back for the header. Control IDs come from `r2k.exe`'s RT_DIALOG
  resources: `python tools/dialogs.py Response/r2k.exe` (needs `pefile`) lists them; the output
  is in `docs/r2k-dialogs.txt`. With no input, Quick Define is opened and finished with every
  default, which is what File > New gives.
- **Solve** is a posted `WM_COMMAND` 5092. Wine gives no "solve finished" signal, so the solve
  counts as finished once the bottom control curve has not changed for 1 s **and** Response's
  process has used under 10 % of a processor over 0.2 s (`session.Cpu`, from `/proc/PID/stat`).
  Response adds a point every 0.05 to 0.5 s while solving at 60 to 80 % of a processor. A solve
  fails after 300 s without a new stage. **More Detail** (11845) is posted after the solve and
  each press is waited for the same way; a press that changes nothing ends it (Response stops at
  327 stages).
- **Copy Chart Data** is the second item of a chart's right-click menu. Before choosing it the
  worker checks that the open menu is a data chart's (`popuprect`: as wide as the control
  charts' menus), since a picture's menu has a different second item; every export's
  `Title :` line is checked against the chart expected. A copy that gets no reply (about one in
  several thousand) is dismissed and tried again, up to three times.
- **Detail views** are chosen in the view list, the only drop-down on the solution screen
  (`cbitems`, `cbget`, `cbselect`; the helper sends the change notification, so the view is in
  place when it replies). Which cells hold which charts is in `src/r2x/views.json`, read by
  `r2x/views.py`; a chart in several views is copied in each and must be the same bytes.
- **Stages.** `identify.py` tells which stages a Longitudinal Strain export can belong to: εx
  (the profile's strain at y = 0) against an εx control curve, and curvature against Moment–φ,
  whichever there are, with units from the axis titles. Shear–γxy is no key: its γxy is
  weighted by the section's widths. `export.py` identifies the stage on screen (the peak); if
  several match (common with shear), `Pager.find` pages from stage 0 and takes the one whose
  exports are the same bytes, and stops rather than guess if none or several are. Other stages
  are reached by paging (PgUp, PgDn), each step checked the same way. With Shear–γxy on top, or
  repeated control points, each look also copies General's Shear Strain, which changes every
  stage.
- `runner.py` writes the record (`r2x/record.py`) under a temporary name until it is complete,
  after the report.
- **Progress** goes to stderr in the fixed form of `r2x/progress.py`, which the command line
  parses. Exit status: 0 solved, 1 failed, 2 usage error (e.g. a stage past the last), 3
  reserved.

## How a define step works

One container run per step (`docker run -i`), so a section is always the file Response wrote:

1. Response opens the section's file (for `define quick` with no file, it starts empty).
2. The dialog is opened with its menu command and its fields are gone through in order
   (`src/r2x/dialogs.json`, read by `r2x/catalogue.py`). For each, the worker reads what the
   dialog shows (value, label and unit, which can change, and the frame it sits in) and asks.
   A field is set only when the answer differs, so Enter leaves it exactly as Response had it.
   Disabled fields are skipped.
3. After every action the worker passes on any dialog Response has opened: Yes/No questions,
   messages, the Reinforcement Types list (its rows are `rebar.dat`'s lines), View Data. A
   dialog it does not recognise stops the step with its text.
4. OK (or Finish), or Cancel if nothing changed; a new section gets today's date from the
   Windows side, since the container's clock is UTC.
5. File > Save As through Wine's common dialog (24334) to the job's folder; the bytes are then
   written over the section's file, under a temporary name first.
6. The dialog is read back for the `set:` line, and the report is rewritten with Response's
   input screen.

The worker and the command line talk one JSON object per line (`src/r2x/ask.py`): `ask` (a
question, with its frame's text), `say`, `set`, `done`. End of input means the person gave up:
the worker stops without saving.

**Frames.** A frame's text can carry the meaning of the fields in it (Top/Bottom for a
rectangle, Outer/Inner Ring for a circle, around the same controls), so it is read from the
dialog as the question is asked, never fixed in the catalogue: the innermost visible group box
whose rectangle encloses the field's control. The command line prints it once as a heading.

**Units first.** Quick Define's defaults follow the units in effect, so `define quick` on an
existing file opens it first, and `define units` before any section is remembered for the
`define quick` that follows.

**Helper commands for define:** `ctls`, `enabled`, `lbitems`/`lbget`/`lbselect` (list boxes),
`psget`/`psselect` (property sheets), `lvitems`/`lvget`/`lvselect` (list views, the shape
pickers: their messages carry pointers, put into Response's process with `VirtualAllocEx` and
read back with `ReadProcessMemory`), and `sclick`. `settext`, `sclick` and the select commands
send with a 0.8 s timeout and reply `ok busy` while Response shows a dialog of its own.

Every dialog's fields, control IDs and menu commands are in `docs/dialogs.md`
(`python tools/define_survey.py` prints its table).

## The report

`src/r2x/report.py`, built in the container. Pictures come from the helper's `snap`: a copy of
a window from its own DC into a BMP, repeated until two in a row are the same (under Wine each
top-level window draws into its own surface, so the screen DC shows only the desktop).
`images.py` makes PNGs. The inputs are taken before solving, the outputs right after the solve,
before any paging. The page is self-contained, and reloads itself: every 1.5 s it loads itself,
hidden, in a frame, and that copy posts its stamp (a hash of the page) back and stops; a
different stamp means the file changed. A reload while the page is out of sight flags its title
(`● Solved`, `● Updated`) until it is looked at, through `window.name`, which survives the
reload.

`prefix.py` sets Wine's X11 driver to unmanaged windows (Xvfb has no window manager, and Wine
waits 2 s for one whenever a dialog closes otherwise) and adds a copy of Wine's Symbol font with
a Windows symbol map, so Response's εx and φ draw in the pictures.

## Running without Docker

Ubuntu 24.04 (or WSL) with:

```bash
sudo dpkg --add-architecture i386 && sudo apt-get update
sudo apt-get install -y wine wine32:i386 wine64 fonts-wine fonts-liberation xvfb mingw-w64 \
    python3-venv
python3 -m venv ~/.venvs/r2x && . ~/.venvs/r2x/bin/activate
pip install -e '.[dev,server]'     # server: the image's packages, fontTools among them
```

With Response's program folder in `./Response`:

```bash
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/Newbeam.r2x.txt --response-dir Response
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/all.r2x.txt --stage all --response-dir Response
python -m r2x.worker --new /tmp/new.r2x.txt --response-dir Response       # File > New
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/Newbeam.r2x.txt --report /tmp/Newbeam.html \
    --response-dir Response
python -m r2x.worker define quick --out /tmp/new.r2t --report /tmp/new.r2x.html \
    --response-dir Response               # one define step: questions on stdout (JSON lines)
python tests/define_driver.py long add web -- @in=$PWD/x.r2t @out=$PWD/x.r2t number=2 bar=15M
```

The first run creates a Wine prefix in `~/.cache/r2x/prefix` and builds the helper there.

## Tests

```bash
pytest                                  # no Wine: the command line against a fake docker
R2X_RESPONSE_DIR=$PWD/Response pytest   # everything, under Wine (about 10 min)
```

- `tests/fake_docker.py` stands in for docker (`R2X_DOCKER="python tests/fake_docker.py"`): by
  default it imitates the worker; with `FAKE_DOCKER_MODE=wine` it runs the real worker on the
  host, with a copy of the prefix per input and the linked folder as `R2X_RESPONSE_DIR`.
  `tests/conftest.py` links a folder for every test: Response itself under Wine, a stand-in
  otherwise.
- **Reference cases** (`tests/reference/`): exports copied by hand in Response on Windows,
  sharing no code with r2x; `capture.ps1` only saves the clipboard to the right file name.
  `tests/test_worker_wine.py` compares the record with them byte for byte. Adding a case:
  `tests/reference/README.md`.
- **Define cases** (`tests/reference/define/`): sections made by hand on Windows (`hand.r2t`)
  and by an r2x session from the same answers; `check.ps1` compares them on Windows,
  `tests/test_define_cases_wine.py` under Wine. `cases.json` holds the answers;
  `tools/define_cases.py` writes each case's files from it.
- **Checks on records alone** (Tier C, `docs/risk-register.md`): `python tools/tier_c.py
  RECORD SECTION ...` checks equilibrium, stage order and the squash load; `--same A B`
  compares two records of one solve. `tests/test_tier_c.py` runs it on the Windows references.
- Rerun the Wine tests on any change to Wine, the image or r2x.

## Releasing

On the Framework, from the repo in WSL (Docker is in WSL Ubuntu, not Windows):

1. `git fetch` and check out the branch to release; the version is in `pyproject.toml` and
   `src/r2x/__init__.py`.
2. `docker build -t ghcr.io/maczout/r2x:VERSION .`
3. In Windows: `py -m pip install --force-reinstall --no-cache-dir
   https://github.com/maczout/r2x/archive/refs/heads/BRANCH.zip` (without the two flags pip
   keeps the old client), then `r2x setup --response FOLDER` once, `r2x health` (client and
   image versions), `check.ps1` in `tests/reference/define`, and a solve or two.
4. Merge into `main` (fast-forward), tag and push from Jamie's machine: `git tag vVERSION &&
   git push origin main vVERSION` (a cloud session cannot push tags).
5. `docker push ghcr.io/maczout/r2x:VERSION`, the image just checked. Once: `gh auth refresh -s
   write:packages`, then `gh auth token | docker login ghcr.io -u maczout --password-stdin`.
   The first push makes the package private: set it to public in the package's settings on
   GitHub, so `r2x setup` can pull it.
6. Reinstall the client from the tag, as the README says.

`docker save ghcr.io/maczout/r2x:VERSION | gzip > r2x-VERSION.tar.gz` keeps a copy offline.
For a local build under another name, set `R2X_IMAGE` to it.

## Server (optional, not used by the command line)

`python -m r2x.server` (settings in `src/r2x/server/__main__.py`) runs a FastAPI app with a
token, a job queue and `R2X_WORKERS` workers, each with its own display and prefix copy. It
reads Response from `R2X_RESPONSE_DIR`, so mount the folder there:
`docker run -d -p 8000:8000 -v FOLDER:/opt/response:ro -e R2X_TOKEN=... IMAGE python -m
r2x.server`. `tests/test_server.py` covers the API with a stand-in for Response.
