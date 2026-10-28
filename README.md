# r2x

Run Response-2000 from the command line.

r2x drives an unmodified copy of Response-2000, Bentz and Collins' sectional analysis program for
reinforced and prestressed concrete, under Wine in a Linux container. It returns Response's own
exported data, byte for byte, and does not re-compute, filter or interpret anything.

**Scope:** the sectional response (Solve → Sectional Response) to axial load, moment and shear,
optionally refined with Solve → More Detail: both control charts, and every chart with a data
export in four detail views, **General**, **Cracking**, **Reinforcement** and **No Shear** (21
charts in all). Input is any file Response-2000 opens (`.r2t`, `.rsp`), or none, which gives
the section File > New gives. Not M–N, M–V or N–V interaction, and not full-member analysis.

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
- **`NAME.r2x.html`, the report** (`--report`). Screenshots for checking by eye that r2x drove
  Response as intended, with an index down the left: under **Inputs**, Response's window before
  solving and the Preferences and Define Loading dialogs as r2x leaves them; under **Outputs**,
  Response's window in each captured view at the peak stage. No data; the screenshots are taken
  under Wine.

Charts that Response shows only as pictures (cross section, crack diagram, internal forces, N+M)
have no data export, so they appear in the report's screenshots and nowhere else. Not captured:
the Load Deformation Plot (a whole-member result) and Mohr's Circles.

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
r2x solve .\Newbeam.r2t --increment 0,1,1     # moment and shear, M/V = 1 m
r2x solve .\Newbeam.r2t --more-detail 2       # refined twice with Solve > More Detail
r2x solve .\col.rsp --units si --initial -2000,0,0 --increment 0,1,0
r2x solve .\cases\*.r2t --out .\results --parallel 4
r2x solve .\Newbeam.r2t --stdout | py parse.py   # the record on stdout, no files
```

- **Settings are overrides.** `--units`, `--factors`, `--initial` and `--increment` are applied
  through Response's own dialogs; r2x never edits the input. Loads are N,M,V, as Define Loading
  has them. An option left out keeps the input's value, or Response's start-up default. The
  settings in effect are in the record header.
- **More Detail.** `--more-detail N` presses Solve → More Detail N times after the solve (`max`:
  until Response refines no further, which it stops doing at 327 stages). Stage numbers are the
  refined solve's.
- **Results** go next to each input, or to `--out`. An existing result is replaced only with
  `--overwrite`.
- **Progress** goes to stderr, with a status line when stderr is a terminal; `-q` shows errors
  only.
- **Exit status:** 0 solved, 1 failed, 2 usage error, 3 out of scope (reserved: since 0.3.0
  nothing is); with several inputs, the most serious of these (1, then 2, then 3).
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
Response** (and **More Detail**, if asked), then reads every chart with **Copy Chart Data** from
the clipboard, paging through the load stages and checking each one against the control curves.
At each stage it goes through the detail views with Response's view list. Every container has its own
display and Wine prefix, so several run at once (`--parallel`). `docs/development.md` has the
details and how to run it without Docker.

## Verification

Each reference case was solved in Response-2000 on Windows and its charts copied by hand
(`tests/reference/`). r2x's record matches every one byte for byte: the control charts at every
stage and the five No Shear charts at the peak in every case, and all 21 charts of the four
views for Newbeam at the peak and 20 stages below it and for the shear and More Detail cases.
One known exception: two exports of the moment-and-shear case at stage 20 each have one zero
printed with the opposite sign (`-0.0000` against `0.0000`), floating-point noise under Wine.

| Case | Settings | Stages, peak |
|---|---|---|
| Newbeam (250 × 600 rectangle, 3–25M / 1–20M) | none: moment increment; every view at stages 56 and 36 | 60, peak 56 |
| Newbeam, US units | `--units us` | 60, peak 56 |
| Newbeam, CSA factors | `--factors csa` | 57, peak 46 |
| Newbeam, axial load | `--initial=-2000,0,0` | 46, peak 37 |
| Newbeam, axial increment only | `--increment=-1,0,0` | 35, peak 22 |
| No input (File > New) | none | 60, peak 56 |
| Newbeam, moment and shear (M/V = 1 m) | `--increment 0,1,1`; every view at stages 30 and 20 | 43, peak 30 |
| Newbeam, shear alone | `--increment 0,0,1`; every view | 52, peak 16 |
| Newbeam, More Detail twice | `--more-detail 2`; every view | 228, peak 224 |

Other stages, and other cases' views, rely on r2x's own checks: each stage is identified from its strain
profile against the control curves before it is copied, and Longitudinal Strain, which every
view shows, must export the same bytes in each view, as must any other chart two views share. The report's pictures are checked by
eye against Windows. Rerun the tests (`docs/development.md`) on any change to Wine, the image or
r2x.

**Shear and More Detail (0.3.0)** are checked on Windows by the last three cases; other
loadings (Newbeam under N and V, Response's own shear examples) rely on r2x's own checks under
Wine. With shear, the strain profile can match several stages near the peak, and then r2x tells
them apart by their exports (`docs/cli.md`, *Shear and More Detail*).

Two heuristics are worth knowing. Wine gives no "solve finished" signal, so the solve counts as
finished once the bottom control curve has not changed for 1 s and Response's process is idle.
Copy Chart Data is chosen by its position in each chart's right-click menu; every export's title
is checked, and r2x opens a menu item only if the menu is a data chart's (charts that are only
pictures have a different menu), so a change there fails loudly.

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
