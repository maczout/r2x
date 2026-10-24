# Newbeam

250 × 600 rectangle, 3–25M bottom / 1–20M top, moment only.

Exports: both control curves, and the five No Shear charts at the stage Response opens on after
solving (maximum moment, M = 336.8 kNm). The Wine spike identified that stage as 56 of 0–59 by
matching curvature to the Moment–φ curve, so the charts are filed under `stages/056/`.

## How these were made

1. Start Response-2000 on Windows and open `input.r2t` from this folder.
2. **Solve → Sectional Response.** Do not use More Detail, and do not change the load stage.
3. Check the view is **No Shear** and the status bar shows M : 336.8 kNm.
4. In PowerShell, from this folder:
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1`
   For each chart it names, right-click that chart → **Copy Chart Data**, then press Enter.

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response version (Help → About) | |
| By | |
