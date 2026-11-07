# Newbeam, axial load, moment and shear all increasing

**To capture** (first verification pass, `docs/risk-register.md`, S9). Newbeam (`input.r2t`,
the same file as `../newbeam/input.r2t`) with an increment in all three of N, M and V: axial
compression growing with the moment and shear (−1 kN per kNm, M/V = 1 m). No increment with
all three has been checked on Windows.

## Settings, applied by hand

**Loads → Sectional Loads** (the "Define Loading" dialog):

| | Constant | Increment |
|---|---|---|
| Axial Load (kN) | 0 | −1 |
| Moment (kNm) | 0 | 1 |
| Shear (kN) | 0 | 1 |

r2x: `--increment=-1,1,1`.

## Exports to capture

The routine in `../README.md`, *Adding a case*, with every view, at the stage Response opens
on; Save As `saved.r2t` as step 2 says.

## What r2x gives under Wine (2026-11-07, r2x 0.5.0)

46 stages (0–45); Shear–γxy on top, Moment–φ below (as with V and M, the N in the increment
does not change the control charts); Response opens on **stage 39**: V 221.6 kN, M 221.6 kNm,
curvature 4.560 mrad/m, γxy 2.784.

## Capture

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response | 1.9.7, `r2k.exe` SHA-256 `bbf4bc59…4e74` |
| By | |
