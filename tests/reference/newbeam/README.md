# Newbeam

250 × 600 rectangle, 3–25M bottom / 1–20M top, moment only.

Exports: both control curves, and the five No Shear charts at the stage Response opens on after
solving (maximum moment, M = 336.8 kNm). The Wine spike identified that stage as 56 of 0–59 by
matching curvature to the Moment–φ curve, so the charts are filed under `stages/056/`.

To come for r2x 0.2.0 (*The other views* below): the 16 charts of the General, Cracking and
Reinforcement views at stage 56, and optionally every view's 21 charts 20 stages below the peak
in `stages/peak-20/`, renamed to the stage number once r2x has identified it.

## How these were made

1. Start Response-2000 on Windows and open `input.r2t` from this folder.
2. **Solve → Sectional Response.** Do not use More Detail, and do not change the load stage.
3. Check the view is **No Shear** and the status bar shows M : 336.8 kNm.
4. In PowerShell, from this folder:
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1 -Stage 056`
   (stage 056 was known from the Wine spike; new cases capture into `stages\peak`).
   For each chart it names, right-click that chart → **Copy Chart Data**, then press Enter.

| Captured | Notes |
|---|---|
| Date | October 24 2026 |
| Windows version | Windows 11 Pro |
| Response version (Help → About) | 1.9.7 |
| By | Jamie McIntyre |

## The other views (r2x 0.2.0)

1. Open `input.r2t` in Response on Windows and **Solve → Sectional Response**. Don't page. Check
   the status bar shows M : 336.8 kNm.
2. In PowerShell, from this folder:
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1 -Stage 056`
   It keeps the seven files already here and asks for the 16 new charts a view at a time. When it
   says, switch the view list under "Nine Graphs" to the view it names; then for each chart it
   names, right-click it → **Copy Chart Data**, then press Enter. It checks each title.
3. Optional, a stage below the peak: press **PgDn** 20 times (the list can keep focus; PgDn still
   pages), then
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1 -Stage peak-20`
   It asks for all 21 charts, No Shear included, into `stages\peak-20`. Note the status bar's M.
4. Commit the new files, or say where they are, and fill in the table below.

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response version (Help → About) | |
| Status bar at peak-20 (M) | |
| By | |
