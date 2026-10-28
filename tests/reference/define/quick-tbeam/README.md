# define case: quick-tbeam

Quick Define: a T-beam with two layers of bottom bars.

**By hand**, in Response-2000 on Windows (anything not listed stays as Response shows it):

1. Start Response-2000 with no file.
2. Define > Quick Define. Set only these, pressing Next after each page and Finish after the last:
   - Step 1 of 4: Title: T-beam; Analysis By: JM; Concrete Cylinder Strength: 40 MPa; Long. Steel Yield Strength: 450 MPa; Transverse Steel Yield: 420 MPa; Prestressed Steel Type: None
   - Step 2 of 4: Shape: T-Beam; btop: 900 mm; h: 1200 mm; bweb: 300 mm; ttop: 200 mm
   - Step 3 of 4: Top, Number of Bars: 4; Bottom, Number of Bars: 6; Bottom, Bar Designation: 30M
   - Step 4 of 4: Stirrup Type: Closed Stirrup; Stirrups, Bar Designation: 15M; Spacing: 300 mm; Clear Cover: 50 mm
3. File > Save As `hand.r2t` in this folder.

**By r2x:** `..\check.ps1` runs `session.txt` in an r2x session in this folder (it makes
`r2x.r2t`) and compares it with
`hand.r2t`, byte for byte, but for the date.
`tests/test_define_cases_wine.py` does the same under Wine.

Written by `tools/define_cases.py` from `cases.json`.
