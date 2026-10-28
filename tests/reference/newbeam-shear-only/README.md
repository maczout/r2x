# Newbeam, shear alone

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`) under shear increasing from zero,
with no moment and no axial load.

## Settings, applied by hand

**Loads → Sectional Loads** (the "Define Loading" dialog):

| | Constant | Increment |
|---|---|---|
| Axial Load (kN) | 0 | 0 |
| Moment (kNm) | 0 | 0 |
| Shear (kN) | 0 | 1 |

## Exports

Both control curves, 52 stages (0–51): `Control : Shear - |g_x_y` on top (`control/shear_gxy`)
and `Control : Shear - |e_x` below (`control/shear_ex`), shear against εx, the strain at
mid-depth. Every view's charts (21) at **stage 16**, the stage Response opens on after solving,
in the **General** view: status bar V 217.7 kN (εx 0.038 mm/m on the control curve), identified
by εx against Shear–εx.

εx is 0 until the section cracks, so the Longitudinal Strain export is the same at stages 1 to
9; r2x tells such stages apart by the General view's Shear Strain.

r2x 0.3.0 under Wine 9.0 (2026-10-27) gives every file byte for byte.

## `saved.r2t`

Response's own **Save As** after setting the loads:
`<sectloading MM="0.000" MV="1.000"/>`, the moment and shear increments. Response leaves out
an increment that is at its default: axial 0, moment 1, shear 0. Solving `saved.r2t` reproduces
these exports byte for byte (r2x 0.3.0 under Wine 9.0, 2026-10-27).

## Capture

The routine in `../README.md`, *Adding a case*, with every view.

| Captured | Notes |
|---|---|
| Date | October 27, 2026 |
| Windows version | Windows 11 Pro |
| Response | 1.9.7, `r2k.exe` SHA-256 `bbf4bc59…4e74` |
| By | Jamie McIntyre |
