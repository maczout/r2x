# define case: add-delete

Add a layer, then delete it: Newbeam as opened and saved.

**By hand**, in Response-2000 on Windows (anything not listed stays as Response shows it):

1. File > Open `..\..\newbeam\input.r2t` (Newbeam).
2. Define > Longitudinal Reinforcement, Individual Layers: type web in Name, then set:
   - Number of Bars: 2
   - Bar Designation: 15M
   - Dist. from Bottom: 300 mm
   - then press Add, and OK
3. Define > Longitudinal Reinforcement, Individual Layers: select web in the list, press Delete, then OK.
4. File > Save As `hand.r2t` in this folder.

**By r2x:** `..\check.ps1` runs `session.txt` in an r2x session in this folder (it makes
`r2x.r2t` from a copy of Newbeam) and compares it with
`hand.r2t`, byte for byte.
`tests/test_define_cases_wine.py` does the same under Wine.

Written by `tools/define_cases.py` from `cases.json`.
