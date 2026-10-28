# Newbeam, More Detail twice

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`) as it is (moment increment),
solved and then refined with **Solve → More Detail** twice.

## Exports

Both control curves (Moment–εx and Moment–φ), 228 stages (0–227), and every view's charts (21)
at **stage 224**, the stage Response shows after the second press, in the **No Shear** view:
status bar M 336.8 kNm, identified by curvature (40.389 mrad/m) and by εx at mid-depth.

Each press puts a new stage between every two stages up to the peak, and none after it: 60,
then 116, then 228 stages. The stage on screen stays the peak (56, then 112, then 224), and the
old points keep their lines in the control charts' exports, byte for byte (seen under Wine).

r2x 0.3.0 under Wine 9.0 (2026-10-27), `--more-detail 2`, gives every file byte for byte.

## The limit

On Windows, **More Detail** is greyed out in the Solve menu after a third press. Under Wine
the third press reaches 327 stages and a fourth changes nothing, with no message. r2x posts
the command without opening the menu, so it sees a press that changes nothing and stops
(`--more-detail max`, or a note when fewer presses took effect than asked).

## No `saved.r2t`

More Detail is not part of the input; the case needs no settings.

## Capture

The routine in `../README.md`, *Adding a case*, with every view, after **Solve → Sectional
Response** and **Solve → More Detail** twice.

| Captured | Notes |
|---|---|
| Date | October 27, 2026 |
| Windows version | Windows 11 Pro |
| Response | 1.9.7, `r2k.exe` SHA-256 `bbf4bc59…4e74` |
| More Detail after the third press | greyed out |
| By | Jamie McIntyre |
