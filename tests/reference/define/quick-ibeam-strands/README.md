# define case: quick-ibeam-strands

Quick Define: an I-beam with 12 strands.

**By hand**, in Response-2000 on Windows (anything not listed stays as Response shows it):

1. Start Response-2000 with no file.
2. Define > Quick Define. Set only these, pressing Next after each page and Finish after the last:
   - Step 1 of 4: Title: I-girder; Concrete Cylinder Strength: 60 MPa
   - Step 2 of 4: Shape: I-Beam; btop: 600 mm; h: 1000 mm; bweb: 150 mm; ttop: 150 mm; tbot: 200 mm; bbot: 450 mm
   - Step 3 of 4: Top, Number of Bars: 2; Top, Bar Designation: 15M; Bottom, Number of Bars: 2; Bottom, Bar Designation: 15M
   - Step 4 of 4: Stirrup Type: Open Stirrup; Spacing: 400 mm; Number of 13 mm strands: 12
3. File > Save As `hand.r2t` in this folder.

**By r2x:** `..\check.ps1` runs `session.txt` in an r2x session in this folder (it makes
`r2x.r2t`) and compares it with
`hand.r2t`, byte for byte, but for the date.
`tests/test_define_cases_wine.py` does the same under Wine.

Written by `tools/define_cases.py` from `cases.json`.
