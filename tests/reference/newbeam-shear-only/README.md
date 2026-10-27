# Newbeam, shear alone (to be captured)

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`) under shear increasing from zero,
with no moment and no axial load.

## Settings, applied by hand

**Loads → Sectional Loads** (the "Define Loading" dialog):

| | Constant | Increment |
|---|---|---|
| Axial Load (kN) | 0 | 0 |
| Moment (kNm) | 0 | 0 |
| Shear (kN) | 0 | 1 |

## What r2x 0.3.0 finds under Wine (2026-10-27)

`r2x solve input.r2t --increment 0,0,1`: 52 stages (0–51), peak **16**.

- Control charts: `Control : Shear - |g_x_y` on top (`control/shear_gxy`), `Control : Shear - |e_x`
  below (`control/shear_ex`): shear against εx, the strain at mid-depth.
- Response opens on the **General** view, at stage 16: V = 217.71 kN (εx 0.038 mm/m on the
  control curve).
- εx is 0 until the section cracks, so the Longitudinal Strain export is the same at stages 1
  to 9; r2x tells them apart by Shear Strain.

## Capture

1. Open `input.r2t` in Response on Windows, set the loads above in **Loads → Sectional Loads**,
   **Save As** `saved.r2t` (outside this folder, then copy it in), and **Solve → Sectional
   Response**. Don't use More Detail and don't page.
2. Screenshot the window with its status bar. Note the view it opens on and the status bar's V.
3. In PowerShell, from this folder:
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1`
   It asks for both control charts, then every view's charts into `stages\peak`.
4. Commit the files, or say where they are, and fill in the table below. Claude renames
   `stages\peak` once its strain profile is matched to the control curves (εx against Shear–εx).

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response version (Help → About) | |
| View Response opened on | |
| Status bar at the peak (V) | |
| By | |
