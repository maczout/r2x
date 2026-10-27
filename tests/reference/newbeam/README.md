# Newbeam

250 × 600 rectangle, 3–25M bottom / 1–20M top, moment only.

Exports: both control curves, and every view's 21 charts (General, Cracking, Reinforcement, No
Shear) at two stages:

- `stages/056/`: the stage Response opens on after solving (maximum moment, M = 336.8 kNm). The
  Wine spike identified it as 56 of 0–59 by matching curvature to the Moment–φ curve. The five No
  Shear charts were captured on 2026-10-24, the other 16 on 2026-10-26 (*The other views*).
- `stages/036/`: 20 stages below the peak (PgDn 20 times; M = 305.6 kNm), captured on 2026-10-26
  as `stages/peak-20/`. Its strain profile matches stage 36 of the control curves (εx and
  curvature), and so does M (305.573 kNm), so it was renamed.

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
| Date | October 26 2026 |
| Windows version | Windows 11 Pro (as on 2026-10-24) |
| Response version (Help → About) | 1.9.7 (as on 2026-10-24) |
| Status bar at peak-20 (M) | 305.6 kNm: stage 36 |
| By | Jamie McIntyre |

All 37 files matched r2x 0.2.0's record of `--stage all` byte for byte, and the record from the
Framework's container matched the cloud's (SHA-256 `8f94ae63…31a0`).
