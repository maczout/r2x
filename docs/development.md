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
python -m r2x.worker tests/reference/newbeam/input.r2t /tmp/Newbeam_r2x --response-dir Response
R2X_RESPONSE_DIR=Response pytest        # includes the end-to-end Newbeam test
```

The first run creates a Wine prefix in `~/.cache/r2x/prefix` and builds the helper there.
Each job runs Response from a fresh temporary copy of its program folder.

## How the worker drives Response

- `src/r2x/worker/helper.c` is a small Win32 program that runs in the same Wine prefix as
  Response and answers one command per line on stdin: list windows, post messages, read the
  clipboard as raw CF_TEXT bytes. It is compiled with mingw-w64 on first use.
- `session.py` uses it to solve (posted `WM_COMMAND` 5092), find the charts, and run
  **Copy Chart Data** by right-clicking a chart and choosing the second menu item. Every export's
  `Title :` line is checked against the expected chart.
- `export.py` pages down to stage 0, then up through every stage. Each stage is checked by
  comparing the curvature of its Longitudinal Strain export with the Moment–φ curve.

Known heuristic: Wine gives no readable "solve finished" signal, so the solve counts as finished
once the Moment–φ curve has not changed for 1 s (Response extends it about every 0.2 s while
solving). Background in `docs/wine-spike.md`.

## Container image

`Dockerfile` builds the server image: Ubuntu 24.04, Wine pinned to `9.0~repack-4build3`, the
helper compiled in a build stage, and the 32-bit Wine prefix created at build time. The build
fails unless `Response/r2k.exe` has the verified SHA-256 (build args `WINE_VERSION`,
`R2K_SHA256` and `RESPONSE_DIR` override the defaults).

```bash
docker build -t r2x-server .
mkdir -p out                         # the container runs as uid 1000
docker run --rm -v "$PWD/tests/reference/newbeam/input.r2t:/in/Newbeam.r2t:ro" \
    -v "$PWD/out:/out" r2x-server python -m r2x.worker /in/Newbeam.r2t /out/Newbeam_r2x
```

The image's default command is the server (`python -m r2x.server`).

Image size is about 1.3 GB compressed (Wine with its 32-bit libraries is most of it).

Inputs outside the scope fail with a reason rather than writing files: an analysis whose control
charts are Shear–γxy (Response's shear examples) stops at the first export-title check.

## Server

`python -m r2x.server` (settings in `src/r2x/server/__main__.py`) runs a FastAPI app and
`R2X_WORKERS` worker threads. At startup each worker gets its own Xvfb display and its own copy of
the prepared Wine prefix (in `R2X_DATA/prefixes/`): Response's exports travel through the
clipboard, which belongs to one wineserver and one X display, so workers must share neither.
Each job zips its output into `R2X_DATA/jobs/<id>/result.zip`.

Checked in a container with two workers: six simultaneous jobs (4 × Newbeam, Cm4.rsp, an invalid
file) all finished; every result was byte-identical to a single run on the host, and the invalid
file failed with Response's own message. About 9 s per Newbeam job; startup takes ~10 s while the
prefix is copied for each worker.

`tests/test_server.py` covers the API with a stand-in for Response (no Wine needed).
