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
