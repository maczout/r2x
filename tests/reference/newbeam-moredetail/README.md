# Newbeam, More Detail twice (to be captured)

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`) as it is (moment increment), solved
and then refined with **Solve → More Detail** twice.

## What r2x 0.3.0 finds under Wine (2026-10-27)

`r2x solve input.r2t --more-detail 2`: 228 stages (0–227), peak **224**.

- Each press puts a new stage between every two stages up to the peak, and none after it: 60,
  then 116, then 228 stages. The old points keep their lines in the control charts' exports,
  byte for byte.
- The stage on screen stays the peak (M = 336.84 kNm, curvature 40.389 mrad/m): stage 56, then
  112, then 224.
- A third press reaches 327 stages and a fourth changes nothing: Response stops refining at 327
  stages, with no message.

## Capture

1. Open `input.r2t` in Response on Windows and **Solve → Sectional Response**, then
   **Solve → More Detail** twice. Don't page.
2. Screenshot the window with its status bar (M should be 336.8 kNm), and note the view.
3. In PowerShell, from this folder:
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1 -Views no-shear`
   It asks for both control charts, then the No Shear view's charts into `stages\peak`.
4. Then, for the limit: press **More Detail** again and look at the Solve menu after it. Is More
   Detail still offered after the third press? Press it a fourth time and say whether anything
   changes (the control curves, a message).
5. Commit the files, or say where they are, and fill in the table below.

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response version (Help → About) | |
| Status bar at the peak (M) | |
| More Detail after the third press | (offered or greyed out; what a fourth press does) |
| By | |
