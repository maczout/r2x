# Newbeam, moment and shear

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`) under moment and shear increasing
together from zero, M/V = 1 m: a shear failure well below the flexural capacity (201.5 kN and
201.5 kNm at the peak, against 336.8 kNm in bending alone).

## Settings, applied by hand

**Loads → Sectional Loads** (the "Define Loading" dialog):

| | Constant | Increment |
|---|---|---|
| Axial Load (kN) | 0 | 0 |
| Moment (kNm) | 0 | 1 |
| Shear (kN) | 0 | 1 |

## Exports

Both control curves, 43 stages (0–42): `Control : Shear - |g_x_y` on top (`control/shear_gxy`)
and `Control : Moment - |f` below (`control/moment_phi`). Every view's charts (21) at two stages,
identified by curvature against Moment–φ:

- **Stage 30**, the stage Response opens on after solving, in the **General** view: status bar
  V 201.5 kN, M 201.5 kNm (curvature 4.254 mrad/m; γxy 1.932 on the top control curve).
- **Stage 20**, ten PgDn below: V 101.9 kN, M 101.8 kNm (curvature 1.640 mrad/m).

r2x 0.3.0 under Wine 9.0 (2026-10-27) gives every file byte for byte, except two exports at
stage 20 that differ only in the sign of a zero: Shear Strain at −274.35 mm is `-0.0000` under
Wine and `0.0000` here, and Shear Stress at −300 mm is `0.0000` under Wine and `-0.0000` here.
That is floating-point noise around zero, near the bottom of the section where shear is nil;
the Wine tests allow it for those two exports only (docs/cli.md, *Shear and More Detail*).

## `saved.r2t`

Response's own **Save As** after setting the loads. It stores the shear increment as
`<sectloading MV="1.000"/>`: Response writes only the increments that differ from its
defaults (axial 0, moment 1, shear 0). It also lists the longitudinal layers by depth, as
Response does when it opens a file. Solving `saved.r2t` reproduces these exports, with the same two signed
zeros at stage 20 (r2x 0.3.0 under Wine 9.0, 2026-10-27).

## Capture

The routine in `../README.md`, *Adding a case*, with every view; then **PgDn** 10 times and
`capture.ps1 -Stage peak-10` for stage 20.

| Captured | Notes |
|---|---|
| Date | October 27, 2026 |
| Windows version | Windows 11 Pro |
| Response | 1.9.7, `r2k.exe` SHA-256 `bbf4bc59…4e74` |
| By | Jamie McIntyre |
