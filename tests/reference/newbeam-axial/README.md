# Newbeam, constant axial compression

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`) under a constant axial
compression of 2000 kN, with the moment increasing.

## Settings, applied by hand

**Loads → Sectional Loads** (the "Define Loading" dialog):

| | Constant | Increment |
|---|---|---|
| Axial Load (kN) | −2000 | 0 |
| Moment (kNm) | 0 | 1.00 (the default) |
| Shear (kN) | 0 | 0 |

## Exports

Both control curves (Moment–εx and Moment–φ, 46 stages, 0–45) and the five No Shear charts at
the stage Response opens on after solving: the maximum moment, **stage 37**. The stage was
identified by matching the Longitudinal Strain export to the control curves, by curvature
(7.111 mrad/m) and by εx at mid-depth (−0.5103 mm/m against −0.510).

Status bar at that stage: N : −1999.9 kN, M : 477.1 kNm, V : 0.0 kN. N shows −1999.9 rather
than −2000, presumably the tolerance on Response's equilibrium iteration.

## `saved.r2t`

Response's own **Save As** after applying the loads. It stores them as
`<sectloading BN="-2000.0"/>` (the increment is the default, so it is not written) and moves the
top bar's element further down the file. Solving `saved.r2t` reproduces these exports byte for
byte (r2x 0.0.1 under Wine 9.0, 2026-10-25).

## Capture

The routine in `../README.md`, *Adding a case*.

| Captured | Notes |
|---|---|
| Date | October 25 2026 |
| Windows version | Windows 11 Pro |
| Response | `r2k.exe` SHA-256 `bbf4bc59…4e74` (see `../../docs/wine-spike.md`) |
| By | Jamie McIntyre |
