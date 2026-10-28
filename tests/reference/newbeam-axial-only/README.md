# Newbeam, axial compression only

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`) under axial compression
increasing from zero, with no moment.

## Settings, applied by hand

**Loads → Sectional Loads** (the "Define Loading" dialog):

| | Constant | Increment |
|---|---|---|
| Axial Load (kN) | 0 | −1 |
| Moment (kNm) | 0 | 0 |
| Shear (kN) | 0 | 0 |

## Exports

With no moment increment, **both** control charts are `Control : Axial Load - |e_x` (axial load
against εx, 35 stages, 0–34), and they are identical. It was captured once, as
`control/axial_ex.txt`. There is no Moment–φ chart.

The five No Shear charts are at the stage Response opens on after solving: the largest
compression, **stage 22**. The stage was identified by εx: the Longitudinal Strain export's value
at mid-depth (−1.6604 mm/m) matches the control curve's εx at stage 22 (−1.660).

Status bar at that stage: N : −5385.3 kN, M : −2.5 kNm, V : 0.0 kN. The moment should be zero;
the −2.5 kNm is a numerical artifact of Response's solution. The curvature is not zero (strain
−2.16 mm/m at the top, −1.16 at the bottom) because the reinforcement is not symmetric.

## `saved.r2t`

Response's own **Save As** after applying the loads: `<sectloading MN="-1.000" MM="0.000"/>`.
Solving `saved.r2t` reproduces these exports byte for byte, as does `--increment -1,0` on
`input.r2t` (`--increment=-1,0,0` since r2x 0.3.0) (r2x under Wine 9.0, 2026-10-25).

## Capture

The routine in `../README.md`, *Adding a case*. The capture script refused the second control
chart as unchanged since the first, and it was skipped.

| Captured | Notes |
|---|---|
| Date | October 25 2026 |
| Windows version | Windows 11 Pro |
| Response | `r2k.exe` SHA-256 `bbf4bc59…4e74` (see `../../docs/wine-spike.md`) |
| By | Jamie McIntyre |
