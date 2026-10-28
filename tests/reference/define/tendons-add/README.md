# define case: tendons-add

Tendons: add 4 strands at 100 mm.

**By hand**, in Response-2000 on Windows (anything not listed stays as Response shows it):

1. File > Open `..\..\newbeam\input.r2t` (Newbeam).
2. Define > Tendons, Define Tendon Layers: type t1 in Name, then set:
   - Number of Strands: 4
   - Strand Designation: S13
   - Prestrain: 6.5 mm/m
   - Dist. from Bottom: 100 mm
   - Slope of Tendon: 0 percent
   - Tendon Type: Low Relax
   - then press Add, and OK
3. File > Save As `hand.r2t` in this folder.

**By r2x:** `..\check.ps1` runs `session.txt` in an r2x session in this folder (it makes
`r2x.r2t` from a copy of Newbeam) and compares it with
`hand.r2t`, byte for byte.
`tests/test_define_cases_wine.py` does the same under Wine.

Written by `tools/define_cases.py` from `cases.json`.
