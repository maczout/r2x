# define case: long-modify

Longitudinal Reinforcement: 4 bars in bot (its depth, shown as 64, becomes 64.00).

**By hand**, in Response-2000 on Windows (anything not listed stays as Response shows it):

1. File > Open `..\..\newbeam\input.r2t` (Newbeam).
2. Define > Longitudinal Reinforcement, Individual Layers: select bot in the list, then set:
   - Number of Bars: 4
   - then press Modify, and OK
3. File > Save As `hand.r2t` in this folder.

**By r2x:** `..\check.ps1` runs `session.txt` in an r2x session in this folder (it makes
`r2x.r2t` from a copy of Newbeam) and compares it with
`hand.r2t`, byte for byte.
`tests/test_define_cases_wine.py` does the same under Wine.

Written by `tools/define_cases.py` from `cases.json`.
