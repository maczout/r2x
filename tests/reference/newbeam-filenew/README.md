# Newbeam from File > New

No input file: a new section from **File → New**, accepting every default of the four Quick
Define pages. The result is Newbeam (Phase 0 found its saved file identical to
`../newbeam/input.r2t` apart from the date), which `r2x solve` with no input reproduces.

## Exports

Both control curves (Moment–εx and Moment–φ, 60 stages, 0–59) and the five No Shear charts at
the stage Response opens on after solving: the maximum moment, **stage 56**, identified by
curvature (40.389 mrad/m) and by εx at mid-depth (7.787 mm/m).

Status bar at that stage: N : −0.1 kN, M : 336.8 kNm, V : 0.0 kN.

The control curves are byte-identical to `../newbeam`, which was captured by opening
`input.r2t`. The five detail views are not: they list the reinforcement layers in another order
(the top bar before the bottom bars) and differ in the last digit of some depths (267.938 there,
267.937 here). That is Response's own difference between a section defined in memory and the
same section read back from a file; it shows on Windows as under Wine.

## Capture

1. Start Response-2000 on Windows with no file open.
2. **File → New**, then Next, Next, Next and Finish, accepting every default.
3. **Solve → Sectional Response** without changing the load stage.
4. From this folder, `powershell -ExecutionPolicy Bypass -File ..\capture.ps1`; the detail
   views were captured into `stages\peak` and the folder renamed to `stages\056`.

| Captured | Notes |
|---|---|
| Date | October 25 2026 |
| Windows version | Windows 11 Pro |
| Response | `r2k.exe` SHA-256 `bbf4bc59…4e74` (see `../../docs/wine-spike.md`) |
| By | Jamie McIntyre |
