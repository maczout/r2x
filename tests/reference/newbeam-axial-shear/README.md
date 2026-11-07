# Newbeam, constant axial compression with moment and shear

**To capture** (first verification pass, `docs/risk-register.md`, S8). Newbeam (`input.r2t`,
the same file as `../newbeam/input.r2t`) under a constant axial compression of 1000 kN, with
moment and shear increasing together (M/V = 1 m). Shear with an axial load has no Windows
reference yet.

## Settings, applied by hand

**Loads → Sectional Loads** (the "Define Loading" dialog):

| | Constant | Increment |
|---|---|---|
| Axial Load (kN) | −1000 | 0 |
| Moment (kNm) | 0 | 1 |
| Shear (kN) | 0 | 1 |

r2x: `--initial=-1000,0,0 --increment 0,1,1`.

## Exports to capture

The routine in `../README.md`, *Adding a case*, with every view, at the stage Response opens
on; Save As `saved.r2t` as step 2 says.

## What r2x gives under Wine (2026-11-07, r2x 0.5.0)

39 stages (0–38); Shear–γxy on top, Moment–φ below; Response opens on **stage 36**: V 295.8
kN, M 295.9 kNm, curvature 5.456 mrad/m, γxy 6.596.

## Capture

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response | 1.9.7, `r2k.exe` SHA-256 `bbf4bc59…4e74` |
| By | |
