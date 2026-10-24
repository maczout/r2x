# r2x

Run Response-2000 from the command line.

`r2x` drives an unmodified copy of Response-2000 (Bentz & Collins' MCFT sectional analysis program)
in a Linux container under Wine and returns its exported data as raw text. It does not re-compute,
filter or interpret anything.

**Scope:** sectional moment-curvature response with no shear; results from the **No Shear** view.
Tested with Response-2000 1.9.7. Early development.

```
PS> r2x solve .\Newbeam.r2t
[Newbeam] solved: 60 load stages
[Newbeam] exporting stages ........................ 60/60
[Newbeam] done → .\Newbeam_r2x\
```

## How it works

```
r2x CLI (Windows/any)  ──HTTPS+token──▶  r2x server  ──▶  worker: Xvfb + Wine + Response-2000
```

A worker opens the input in Response, runs **Solve → Sectional Response**, steps through every load
stage, and uses each chart's **Copy Chart Data** command to read its data from the clipboard of a
virtual display. Each worker runs one Response instance in its own container.

## Usage

```powershell
py -m pip install git+https://github.com/maczout/r2x
r2x config set server https://your-host
r2x config set token <token>

r2x solve .\Newbeam.r2t                  # one or more files, or a glob
r2x solve .\cases\*.r2t --out .\results
r2x health                               # server, Wine and Response-2000 versions
```

## Output

One folder per input. Files are Response's clipboard text, unedited.

```
Newbeam_r2x/
  input.r2t
  manifest.json            r2x version, Response exe SHA-256, Wine version, input SHA-256,
                           stage count, file list
  control/
    moment_ex.txt          Control : Moment - εx  (all stages)
    moment_phi.txt         Control : Moment - φ   (all stages)
  stages/
    000/                   one folder per load stage, in Response's order
      longitudinal_strain.txt
      shrinkage_thermal_strain.txt
      long_reinforcement_stress.txt
      long_reinf_stress_at_crack.txt
      longitudinal_concrete_stress.txt
    001/
    ...
```

Panels that Response shows only as pictures (cross section, crack diagram, internal forces, N+M)
have no data export and are not included.

## Running the server

Response-2000 is not included. Put its program folder in `./response/` and build:

```bash
docker build -t r2x-server .
docker run -d -p 8000:8000 -e R2X_TOKEN=<token> -e R2X_WORKERS=2 r2x-server
```

The image pins the Wine version and the SHA-256 of `r2k.exe`. Run it on a private network or behind
HTTPS. `R2X_VNC=1` exposes a worker's virtual display in a browser for debugging.

API (bearer token): `POST /jobs` (upload `.r2t`), `GET /jobs/{id}`, `GET /jobs/{id}/result` (zip),
`GET /health`.

## Verification

Exports must match reference cases solved in Response-2000 on Windows, byte for byte (ignoring line
endings). Rerun on any change to Wine, the image or r2x.

| Case | Result |
|---|---|
| Newbeam: 250 × 600 rectangle, 3–25M / 1–20M, moment only; both control curves (60 stages) and all five No Shear charts at peak | Identical |

## Response-2000

Free software by Evan C. Bentz and Michael P. Collins, available from its authors <!-- TODO: link -->.
This project is not affiliated with or endorsed by them or the University of Toronto. Check the
authors' terms before running a service that others use.

## Disclaimer

r2x automates Response-2000; it does not check or validate designs. The engineer of record is
responsible for any use of its results.

## License

MIT (r2x code only).
