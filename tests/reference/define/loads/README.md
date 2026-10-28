# define case: loads

Sectional Loads: N = -2000 kN, increment 0,1,1.

**By hand**, in Response-2000 on Windows (anything not listed stays as Response shows it):

1. File > Open `..\..\newbeam\input.r2t` (Newbeam).
2. Loads > Sectional Loads: set:
   - Axial Load, Constant: -2000 kN
   - Shear, Increment: 1 kN
   - then OK
3. File > Save As `hand.r2t` in this folder.

**By r2x:** `..\check.ps1` runs `session.txt` in an r2x session in this folder (it makes
`r2x.r2t` from a copy of Newbeam) and compares it with
`hand.r2t`, byte for byte.
`tests/test_define_cases_wine.py` does the same under Wine.

Written by `tools/define_cases.py` from `cases.json`.
