# r2x define: reference cases

Thirteen sections, each made twice: by hand in Response-2000 on Windows (`hand.r2t`) and by an
r2x session from the same answers (`session.txt`). They match when they are the same bytes (the
three Quick Define cases but for the date, since Response dates a new section with the day it
is made), or else when they are the same section with the longitudinal layers in another order
and solve to the same record: Response keeps a new section's layers in the order it made them,
which differed between the hand-made Quick Define sections and r2x's, and sorts them by depth
whenever it opens the file (`compare.py`; `docs/define.md`, *Findings*). Cases starting from
Newbeam open `..\newbeam\input.r2t`, so its layers are sorted by depth as in r2x's file chain.

Made by hand so far (2026-10-28): `quick-tbeam`, `quick-column`, `quick-ibeam-strands`. The
column is the same bytes; the T-beam and the I-girder differ only in where one layer sits, and
solve to the same record.

| Case | What it checks |
|---|---|
| `quick-tbeam` | Quick Define: a T-beam, materials, two layers of bottom bars, closed stirrups |
| `quick-column` | Quick Define: a circular column with hoops |
| `quick-ibeam-strands` | Quick Define: an I-beam with 12 strands |
| `add-delete` | a layer added then deleted gives Newbeam as opened and saved |
| `general` | Edit General: title and comments, analysis by, crack spacing, moment axis |
| `materials` | Material Properties: f'c and fpu, fy left as "Detailed" |
| `section` | Concrete Section: Newbeam as a T-beam |
| `long-add` | Longitudinal Reinforcement: a layer added |
| `long-modify` | a layer modified: its depth taken at the dialog's precision (63.90 to 64.00) |
| `trans-modify` | Transverse Reinforcement: spacing and bar type |
| `tendons-add` | Tendons: a layer of strands |
| `loads` | Sectional Loads: constant N, increment M and V |
| `units` | Preferences: US Customary |

## Checking on Windows

1. In Response-2000, make each case's `hand.r2t` as its `README.md` says (Save As into the
   case folder). The first five matter most: the three Quick Define cases, `add-delete` and
   `long-modify`.
2. From this folder: `powershell -ExecutionPolicy Bypass -File check.ps1`. For each case with a
   `hand.r2t` it runs `session.txt` in an r2x session (piped into `r2x`), which writes `r2x.r2t`
   and its report `r2x.r2x.html` in the case folder, and prints `MATCH` or `DIFFERS`;
   `fc.exe /n hand.r2t r2x.r2t` shows where. Where the files differ only in their layers'
   order, it solves both (into `solved\`) and compares the records. The results are also in
   `check-results.txt`, and each session's output in the case's `r2x-session.log`. r2x's files
   are not committed.
3. Commit the `hand.r2t` files: `tests/test_define_cases_wine.py` then compares them under
   Wine on every test run.

`cases.json` holds each case's answers by field; `python tools/define_cases.py` writes the
cases' `session.txt` and `README.md` from it (under Wine), so a changed case is changed there.
