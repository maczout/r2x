# Development

## Running the worker locally (Linux or WSL)

The worker drives Response-2000 under Wine on its own virtual display. It needs Ubuntu 24.04
(or similar) with:

```bash
sudo dpkg --add-architecture i386 && sudo apt-get update
sudo apt-get install -y wine wine32:i386 wine64 fonts-wine fonts-liberation xvfb mingw-w64 \
    python3-venv
```

From the repo (Response-2000 in `./Response`):

```bash
python3 -m venv ~/.venvs/r2x && . ~/.venvs/r2x/bin/activate
pip install -e '.[dev,server]'     # server: the image's packages, fontTools among them
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/Newbeam.r2x.txt --response-dir Response
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/all.r2x.txt --stage all --response-dir Response
python -m r2x.worker --new /tmp/new.r2x.txt --response-dir Response       # no input: File > New
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/Newbeam.r2x.txt --report /tmp/Newbeam.html \
    --response-dir Response
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/shear.r2x.txt --increment=0,1,1 \
    --more-detail 2 --response-dir Response
R2X_RESPONSE_DIR=Response pytest        # includes the end-to-end Newbeam tests
```

The first run creates a Wine prefix in `~/.cache/r2x/prefix` and builds the helper there.
Each job runs Response from a fresh temporary copy of its program folder.

The command line can be tested without Docker: `tests/fake_docker.py` stands in for it
(`R2X_DOCKER="python tests/fake_docker.py"`). By default it imitates the worker; with
`FAKE_DOCKER_MODE=wine` it runs the real worker on the host, with its own copy of the Wine prefix
per input as each container has, so `--parallel` works too. `tests/test_cli_wine.py` uses it.

## How the worker drives Response

- `src/r2x/worker/helper.c` is a small Win32 program that runs in the same Wine prefix as
  Response and answers one command per line on stdin: list windows, post messages, read the
  clipboard as raw CF_TEXT bytes. It is compiled with mingw-w64 on first use.
- `session.py` uses it to solve (posted `WM_COMMAND` 5092), find the charts, and run
  **Copy Chart Data** by right-clicking a chart and choosing the second menu item. Every export's
  `Title :` line is checked against the expected chart. A copy that gets no reply (about one in
  several thousand under Wine) is dismissed and tried again, up to three times. Before choosing
  the item it checks the open menu is a data chart's (`popuprect`: as wide as the control
  charts' menus), since a chart that is only a picture has a menu whose second item toggles its
  drawing.
- **Detail views** are chosen in Response's view list, the only drop-down on the solution screen
  (`cbitems`, `cbget`, `cbselect`; the helper sends the change notification, so the new view is
  in place when it replies). Which grid cells hold which charts in each view is in
  `src/r2x/views.json`, the catalogue `r2x/views.py` reads; `find_charts` maps the view on
  screen. Background in `docs/cli.md`, *All detail views*.
- `dialogs.py` applies `--units`, `--factors`, `--initial` and `--increment` (N, M and V)
  through Response's Preferences and Define Loading dialogs (menu commands 321 and 152), and
  reads the settings in effect back for the record header, with a screenshot of each dialog for
  the report when there is one.
  Control IDs come from `r2k.exe`'s RT_DIALOG resources: `python tools/dialogs.py
  Response/r2k.exe` (needs `pefile`) lists them; the output is in `docs/r2k-dialogs.txt`.
- `identify.py` tells which stages a Longitudinal Strain export can belong to: εx (the
  profile's strain at y = 0) against a control chart's εx curve (Moment–, Axial Load– or
  Shear–εx), and curvature against the Moment–φ curve, whichever there are, with units from the
  axis titles. Shear–γxy is no key (its γxy needs the section's widths). `export.py` identifies
  the stage on screen after the solve, the peak. If several stages match (common with shear),
  `Pager.find` pages from stage 0 to the highest of them and takes the one whose exports are the
  same bytes, and stops rather than guess if none or several are. `--stage peak` (the default)
  otherwise needs no paging. Stages above the peak are reached by paging up from it; for any
  stage below, it pages down until Response stops at stage 0, then up. Every step is checked the
  same way. With Shear–γxy on top, or repeated control points (an increment of 0,0,0), the
  strain profile can stay the same from one stage to the next, so each look also copies the
  General view's Shear Strain (recorded only if General is among the views). At each selected
  stage `export.py` goes through the views (the one on screen first), and every view's
  Longitudinal Strain must be the bytes that identified the stage.
- **More Detail** (`--more-detail`) is menu command 11845, posted after the solve has finished;
  each press is waited for like the solve. A press that changes nothing (Response stops at 327
  stages) ends it, with a note if fewer presses took effect than were asked.
- `runner.py` writes the result as one raw record (`docs/raw-format.md`; reader and writer in
  `r2x/record.py`), under a temporary name until it is complete.
- The worker reports progress on stderr in the fixed form of `r2x/progress.py`, which the command
  line parses. Exit status: 0 solved, 1 failed, 2 usage error (e.g. a stage past the last
  stage), 3 out of scope.

Known heuristic: Wine gives no readable "solve finished" signal, so the solve counts as finished
once the bottom control curve has not changed for 1 s and Response's process has used under
10 % of a processor over 0.2 s (`session.Cpu`, from `/proc/PID/stat` on the Linux side; without
it, the curve alone decides). Response adds a point every 0.05 to 0.5 s while solving and uses
60 to 80 % of a processor. A solve fails after 300 s without a new stage. Background in
`docs/wine-spike.md` and `docs/cli.md` (*Shear and More Detail*).

`prefix.py` prepares the Wine prefix: the runner checks it before every job, and the image runs
it once at build time (`python -m r2x.worker.prefix`). It does two things beyond `wineboot`:

- `HKCU\Software\Wine\X11 Driver` `Managed=N`. Xvfb has no window manager, and with managed
  windows Wine waits 2 s for one every time a dialog closes; unmanaged windows skip the wait. The
  exports are the same either way (the Wine tests pass with both).
- `drive_c/windows/Fonts/r2x-symbol.ttf`, a copy of Wine's Symbol font with a Windows symbol
  cmap (U+F020–U+F0FF) and a higher revision, so Wine prefers it. Response draws Greek letters
  (εx, φ) as Symbol-font characters at those codes; without the map they are boxes. Only the
  report's pictures change. It needs fontTools and Wine's fonts; without them the runner notes
  that the Greek letters will be boxes and carries on.

## Pictures for the report

`--report` uses the helper's `snap` command: it copies a window of Response's from its own window
DC into a BMP, repeated until two in a row are the same (the screen DC shows only the empty
desktop under Wine, since each top-level window draws into its own surface). `images.py` turns
the BMPs into PNGs and `r2x/report.py` builds the page. Both run in the container; the pictures
never enter the record. The inputs are taken before solving (`runner.py`, `dialogs.read`):
Response's main window with the settings applied, then the Preferences and Define Loading
dialogs. The outputs are taken right after the solve, before any paging (`export.py`): the main
window in each view. Since 0.3.0 the report has no Copy Chart Picture; the helper's `clipemf`
and `clipformats` commands, which played its metafiles, are unused.

## Container image

`Dockerfile` builds the image: Ubuntu 24.04, Wine pinned to `9.0~repack-4build3`, the
helper compiled in a build stage, and the 32-bit Wine prefix created at build time. The build
fails unless `Response/r2k.exe` has the verified SHA-256 (build args `WINE_VERSION`,
`R2K_SHA256` and `RESPONSE_DIR` override the defaults).

```bash
docker build -t r2x .
mkdir -p out                         # the container runs as uid 1000
docker run --rm -v "$PWD/tests/reference/newbeam/input.r2t:/in/Newbeam.r2t:ro" \
    -v "$PWD/out:/out" r2x python -m r2x.worker /in/Newbeam.r2t /out/Newbeam.r2x.txt
```

The `r2x` command line tool runs exactly this, once per input. To run the optional
server instead: `docker run -d -p 8000:8000 -e R2X_TOKEN=<token> -e R2X_WORKERS=2 r2x python -m r2x.server`.

Image size is about 1.3 GB compressed (Wine with its 32-bit libraries is most of it).

Exit status 3 (out of scope) is reserved: until 0.3.0, an analysis with shear stopped with it.

## Server (optional)

Not used by the command line tool. `python -m r2x.server` (settings in `src/r2x/server/__main__.py`) runs a FastAPI app and
`R2X_WORKERS` worker threads. At startup each worker gets its own Xvfb display and its own copy of
the prepared Wine prefix (in `R2X_DATA/prefixes/`): Response's exports travel through the
clipboard, which belongs to one wineserver and one X display, so workers must share neither.
Each job writes its raw record to `R2X_DATA/jobs/<id>/NAME.r2x.txt`; the upload takes an
optional `stage` field, as for `--stage`.

Checked in a container with two workers: six simultaneous jobs (4 × Newbeam, Cm4.rsp, an invalid
file) all finished; every result was byte-identical to a single run on the host, and the invalid
file failed with Response's own message. About 9 s per Newbeam job; startup takes ~10 s while the
prefix is copied for each worker.

`tests/test_server.py` covers the API with a stand-in for Response (no Wine needed).
