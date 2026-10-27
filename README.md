# r2x

Run Response-2000 from the command line.

r2x drives an unmodified copy of Response-2000, Bentz and Collins' sectional analysis program for
reinforced and prestressed concrete, under Wine in a Linux container. It returns Response's own
exported data, byte for byte, and does not re-compute, filter or interpret anything.

**Scope:** the sectional response to axial load and moment, without shear: both control charts,
and every chart with a data export in four detail views, **General**, **Cracking**,
**Reinforcement** and **No Shear** (21 charts in all). Input is any file
Response-2000 opens (`.r2t`, `.rsp`), or none, which gives the section File > New gives. Inputs
whose loading includes shear stop with a reason. Not M–N interaction or full-member analysis.

```
PS> r2x solve .\Newbeam.r2t --report
[Newbeam] solved: 60 stages, peak 56 -> Newbeam.r2x.txt, Newbeam.r2x.html (6.2 s)
```

## Results

- **`NAME.r2x.txt`, the raw record**, one per input. Response's Copy Chart Data text for both
  control charts (every load stage) and the detail views' charts (the peak stage by default),
  each chart once even where it appears in several views, behind
  a header with the r2x, Wine and Response versions, the input's SHA-256 and the settings in
  effect. It is the result, and r2x's contract with whatever reads it: layout and a Python reader
  in `docs/raw-format.md`.
- **`NAME.r2x.html`, the report** (`--report`). The peak stage as Response shows it: the control
  charts, then each detail view: Response's window in that view, and each of its charts as
  **Copy Chart Picture** draws it, beside its data. For reading; the pictures are drawn under
  Wine.

Charts that Response shows only as pictures (cross section, crack diagram, internal forces, N+M)
have no data export, so they appear in the report's window pictures and nowhere else. Not
captured: the Load Deformation Plot (a whole-member result) and Mohr's Circles (deferred).

## Setup (Windows)

1. WSL 2 with Ubuntu 24.04, and Docker Engine inside it: `sudo apt-get install docker.io
   docker-buildx`, then add yourself to the `docker` group.
2. Response-2000 is not included. Download it from its author (see below) and put its program
   folder in `./Response/` in this repo.
3. Build the image once, in Ubuntu from the repo folder: `docker build -t r2x .` The build pins
   the Wine version and stops unless `Response/r2k.exe` has the verified SHA-256.
4. Install the command line tool in Windows (Python 3.10+, no other dependencies):

   ```powershell
   py -m pip install https://github.com/maczout/r2x/archive/main.zip
   ```

`r2x health` shows the image's r2x, Wine and Response versions. On Linux, r2x calls `docker`
directly.

## Usage

```powershell
r2x solve                                    # no input: a new section, as File > New gives
r2x solve .\Newbeam.r2t                      # one or more files, or a glob
r2x solve .\Newbeam.r2t --stage all          # detail views at every stage (default: peak)
r2x solve .\Newbeam.r2t --stage peak,0-5     # or at these stages; 0 is the initial load
r2x solve .\Newbeam.r2t --views no-shear     # only these detail views (default: all four)
r2x solve .\Newbeam.r2t --report             # also the HTML report
r2x solve .\col.rsp --units si --initial -2000,0 --increment 0,1
r2x solve .\cases\*.r2t --out .\results --parallel 4
r2x solve .\Newbeam.r2t --stdout | py parse.py   # the record on stdout, no files
```

- **Settings are overrides.** `--units`, `--factors`, `--initial` and `--increment` are applied
  through Response's own dialogs; r2x never edits the input. An option left out keeps the input's
  value, or Response's start-up default. The settings in effect are in the record header.
- **Results** go next to each input, or to `--out`. An existing result is replaced only with
  `--overwrite`.
- **Progress** goes to stderr, with a status line when stderr is a terminal; `-q` shows errors
  only.
- **Exit status:** 0 solved, 1 failed, 2 usage error, 3 out of scope; with several inputs, the
  most serious of these (1, then 2, then 3).
- **Environment:** `R2X_IMAGE` (image name, default `r2x`), `R2X_DOCKER` (the command that runs
  docker), `R2X_WSL_DISTRO` (the WSL distribution with Docker).

`r2x solve --help` has the details. `docs/cli.md` is the full specification, with the decisions
behind it and what was confirmed in Response on Windows.

## How it works

```
r2x (Windows)  ──docker run──▶  container in WSL: Xvfb + Wine + Response-2000 + helper.exe
```

`r2x solve` runs the container once per input, with the input mounted read-only and the results
written straight to the output folder. Inside, a small Win32 helper drives Response on a virtual
display: it applies the settings through Response's dialogs, runs **Solve → Sectional
Response**, then reads every chart with **Copy Chart Data** from the clipboard, paging through
the load stages and checking each one against the control curves. At each stage it goes through
the detail views with Response's view list. Every container has its own
display and Wine prefix, so several run at once (`--parallel`). `docs/development.md` has the
details and how to run it without Docker.

## Verification

Each reference case was solved in Response-2000 on Windows and its charts copied by hand
(`tests/reference/`). r2x's record matches every one byte for byte: the control charts at every
stage and the five No Shear charts at the peak. Hand captures of Newbeam's other three views
are next; until then those 16 charts rest on r2x's own checks below.

| Case | Settings | Stages, peak |
|---|---|---|
| Newbeam (250 × 600 rectangle, 3–25M / 1–20M) | none: moment increment | 60, peak 56 |
| Newbeam, US units | `--units us` | 60, peak 56 |
| Newbeam, CSA factors | `--factors csa` | 57, peak 46 |
| Newbeam, axial load | `--initial -2000,0` | 46, peak 37 |
| Newbeam, axial increment only | `--increment -1,0` | 35, peak 22 |
| No input (File > New) | none | 60, peak 56 |

Detail views at other stages rely on r2x's own checks: each stage is identified from its strain
profile against the control curves before it is copied, and Longitudinal Strain, which every
view shows, must export the same bytes in each view, as must any other chart two views share. The report's pictures are checked by
eye against Windows. Rerun the tests (`docs/development.md`) on any change to Wine, the image or
r2x.

Two heuristics are worth knowing. Wine gives no "solve finished" signal, so the solve counts as
finished once the bottom control curve has not changed for 1 s. Copy Chart Data and Copy Chart
Picture are chosen by their position in each chart's right-click menu; every export's title is
checked, every picture must be a metafile, and r2x opens a menu item only if the menu is a data
chart's (charts that are only pictures have a different menu), so a change there fails loudly.

## Server (optional, not used by the CLI)

The repo also has an HTTP server (`python -m r2x.server`) for running jobs on another machine: a
token-protected API with a job queue and parallel workers. See `docs/development.md`.

## Response-2000

Response-2000 is free software by Evan C. Bentz and Michael P. Collins, available from Bentz's
site, [hadrianworks.com](https://www.hadrianworks.com/). The authors ask that work using it cite
Bentz's PhD thesis: E. C. Bentz, *Sectional Analysis of Reinforced Concrete Members*, University
of Toronto, 2000. r2x is not affiliated with or endorsed by them or the University of Toronto.
Check the authors' terms before running it as a service for others.

## Disclaimer

r2x automates Response-2000; it does not check or validate designs. The engineer of record is
responsible for any use of its results.

## License

MIT (r2x code only).
