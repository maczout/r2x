# Newbeam, moment and shear (to be captured)

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

## What r2x 0.3.0 finds under Wine (2026-10-27)

`r2x solve input.r2t --increment 0,1,1`: 43 stages (0–42), peak **30**.

- Control charts: `Control : Shear - |g_x_y` on top (`control/shear_gxy`), `Control : Moment - |f`
  below (`control/moment_phi`).
- Response opens on the **General** view, at stage 30: V = 201.53 kN, M = 201.51 kNm (γxy 1.932,
  curvature 4.254 mrad/m on the control curves).
- Stage 20, ten below: V = 101.86 kN, M = 101.81 kNm (curvature 1.640 mrad/m).

## Capture

1. Open `input.r2t` in Response on Windows, set the loads above in **Loads → Sectional Loads**,
   **Save As** `saved.r2t` (outside this folder, then copy it in), and **Solve → Sectional
   Response**. Don't use More Detail and don't page.
2. Screenshot the window with its status bar. Note the view it opens on and the status bar's V
   and M.
3. In PowerShell, from this folder:
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1`
   It asks for the top and the bottom control chart (and names the files from their titles),
   then for every view's charts, a view at a time, into `stages\peak`.
4. Press **PgDn** 10 times, note the status bar's V and M, then
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1 -Stage peak-10`
5. Commit the files, or say where they are, and fill in the table below. Claude renames the stage
   folders once their strain profiles are matched to the control curves (curvature against
   Moment–φ).

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response version (Help → About) | |
| View Response opened on | |
| Status bar at the peak (V, M) | |
| Status bar at peak-10 (V, M) | |
| By | |
