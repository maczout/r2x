# r2x

Run Response-2000 from the command line.

`r2x` drives an unmodified copy of Response-2000 (Bentz & Collins' MCFT sectional analysis program)
in a Linux container under Wine and returns its exported data as raw text. It does not re-compute,
filter or interpret anything.

**Scope:** sectional moment-curvature response with no shear; results from the **No Shear** view.
Input is any file Response-2000 opens (`.r2t`, `.rsp`).
Tested with Response-2000 1.9.7. Early development.

```
PS> r2x solve .\Newbeam.r2t
[Newbeam] solved: 60 load stages
[Newbeam] exported stage 10/60
...
[Newbeam] exported stage 60/60
[Newbeam] done in 9.1 s -> Newbeam_r2x
```

## How it works

```
r2x CLI (Windows)  ──docker run──▶  container (in WSL): Xvfb + Wine + Response-2000
```

`r2x solve` runs the container once per input file, with the input mounted read-only and the result
folder written straight to disk. Inside, Response opens the input, runs **Solve → Sectional
Response**, steps through every load stage, and each chart's **Copy Chart Data** is read from the
clipboard of a virtual display. Every container has its own display and Wine prefix, so several
can run at once (`-j`).

## Setup (Windows)

Needs WSL 2 with Ubuntu 24.04 and Docker Engine inside it (`sudo apt-get install docker.io
docker-buildx`, then add yourself to the `docker` group). Response-2000 is not included: put its
program folder in `./Response/` and build the image once, in Ubuntu from the repo folder:

```bash
docker build -t r2x .
```

The image pins the Wine version and refuses to build unless `r2k.exe` has the verified SHA-256.
Then install the command line tool in Windows (Python 3.10+, no other dependencies):

```powershell
py -m pip install https://github.com/maczout/r2x/archive/main.zip
```

## Usage

The next version of the command line is specified in `docs/cli.md`; this section describes the
current one.

```powershell
r2x solve .\Newbeam.r2t                  # one or more files, or a glob
r2x solve .\cases\*.r2t --out .\results -j 2
r2x health                               # the image's r2x, Wine and Response-2000 versions
```

Results go next to each input unless `--out` is given; an existing result folder is only replaced
with `--force`. The exit code is non-zero if any input failed. On Linux `r2x` calls `docker`
directly; `R2X_IMAGE`, `R2X_DOCKER` and `R2X_WSL_DISTRO` override the defaults.

## Output

One text file per input, `NAME.r2x.txt`: the raw record. It holds Response's Copy Chart Data
text, byte for byte, for both control charts (every stage) and the five No Shear charts that have
a data export, at the peak stage by default. A short header gives the r2x, Wine and Response
versions, the input's SHA-256, the stage count and the peak stage. Layout and a Python reader:
`docs/raw-format.md`.

Panels that Response shows only as pictures (cross section, crack diagram, internal forces, N+M)
have no data export and are not included. Inputs outside the scope (for example an analysis with
shear) fail with a reason instead of producing output.

## Server (optional, not used by the CLI)

The repo also contains an HTTP server (`python -m r2x.server`) for running jobs on another
machine: a token-protected API with a job queue and parallel workers. The CLI does not use it.
See `docs/development.md`.

## Verification

Exports must match reference cases solved in Response-2000 on Windows, byte for byte (ignoring line
endings). Rerun on any change to Wine, the image or r2x.

| Case | Result |
|---|---|
| Newbeam: 250 × 600 rectangle, 3–25M / 1–20M, moment only; both control curves (60 stages) and all five No Shear charts at peak | Identical |

## Response-2000

Free software by Evan C. Bentz and Michael P. Collins, available from its authors <!-- TODO: link -->.
This project is not affiliated with or endorsed by them or the University of Toronto. Check the
authors' terms before running it as a service for others.

## Disclaimer

r2x automates Response-2000; it does not check or validate designs. The engineer of record is
responsible for any use of its results.

## License

MIT (r2x code only).
