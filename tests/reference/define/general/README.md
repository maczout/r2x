# define case: general

Edit General: title, comments, crack spacing, moment axis.

**By hand**, in Response-2000 on Windows (anything not listed stays as Response shows it):

1. File > Open `..\..\newbeam\input.r2t` (Newbeam).
2. Define > Edit General: set:
   - Title: Newbeam edited
   - Comments: by r2x define
   - Analysis By: JM
   - Automatic Longitudinal Spacing: n
   - Longitudinal Spacing: 300 mm
   - Centroidal Moment axis: n
   - Moment axis: 250 mm from bottom
   - then OK
3. File > Save As `hand.r2t` in this folder.

**By r2x:** `..\check.ps1` runs `session.txt` in an r2x session in this folder (it makes
`r2x.r2t` from a copy of Newbeam) and compares it with
`hand.r2t`, byte for byte.
`tests/test_define_cases_wine.py` does the same under Wine.

Written by `tools/define_cases.py` from `cases.json`.
