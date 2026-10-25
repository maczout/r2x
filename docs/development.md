# Development

## Running the worker locally (Linux or WSL)

The worker drives Response-2000 under Wine on its own virtual display. It needs Ubuntu 24.04
(or similar) with:

```bash
sudo dpkg --add-architecture i386 && sudo apt-get update
sudo apt-get install -y wine wine32:i386 wine64 xvfb mingw-w64 python3-venv
```

From the repo (Response-2000 in `./Response`):

```bash
python3 -m venv ~/.venvs/r2x && . ~/.venvs/r2x/bin/activate
pip install -e '.[dev]'
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/Newbeam.r2x.txt --response-dir Response
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/all.r2x.txt --stage all --response-dir Response
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
  several thousand under Wine) is dismissed and tried again, up to three times.
- `export.py` identifies the stage on screen after the solve, the peak, by matching the
  curvature of its Longitudinal Strain export to the Moment–φ curve, and stops rather than guess
  if several stages match. `--stage peak` (the default) needs no paging. Stages above the peak
  are reached by paging up from it; for any stage below, it pages down until Response stops at
  stage 0, then up. Every step is checked the same way.
- `runner.py` writes the result as one raw record (`docs/raw-format.md`; reader and writer in
  `r2x/record.py`), under a temporary name until it is complete.
- The worker reports progress on stderr in the fixed form of `r2x/progress.py`, which the command
  line parses. Exit status: 0 solved, 1 failed, 2 usage error (e.g. a stage past the last
  stage), 3 out of scope.

Known heuristic: Wine gives no readable "solve finished" signal, so the solve counts as finished
once the Moment–φ curve has not changed for 1 s (Response extends it about every 0.2 s while
solving). Background in `docs/wine-spike.md`.

## Container image

`Dockerfile` builds the server image: Ubuntu 24.04, Wine pinned to `9.0~repack-4build3`, the
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

Inputs outside the scope stop with a reason and exit status 3 rather than writing a record: an
analysis with shear (Response's shear examples) is recognised as soon as the solve starts, from
the top control chart's title, Shear–γxy.

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
