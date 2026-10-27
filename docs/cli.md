# Command line

**Status:** agreed 2026-10-25; implemented in full in r2x 0.1.0 (2026-10-25). `--views` added
in r2x 0.2.0 (2026-10-26). Phases 3 to 5 and *All detail views* below record how. `r2x solve --help` matches the text below plus one note, and
`tests/test_cli.py` keeps them in step.

A stage number past the last stage is a usage error (exit status 2), found once the solve has
given the stage count. With several inputs, the exit status is the most serious outcome: 1, then
2, then 3.

## Decisions

- **r2x is a kernel.** It drives Response-2000 and returns Response's own exports. Parsing them
  into a structured schema belongs to the wider toolbox (r2k), so r2x does not have to change as
  that schema evolves, and a real clone can later replace the wrapper behind the same schema.
- **The raw record is the result.** One text file per input. Each section is Response's Copy
  Chart Data text, byte for byte, behind a header with the versions, the input's SHA-256 and the
  settings in effect. Its layout has its own document (`docs/raw-format.md`) and a version
  number, since it is the kernel's contract.
- **Settings go through Response's dialogs only.** r2x never edits the input file, so it does not
  depend on the input format (`.rsp`, XML `.r2t`, or the older Ver_0.8 text `.r2t`).
- **Options are overrides.** An option that is left out keeps the input's value. If the input has
  none, it takes Response's start-up default, i.e. what File > New gives: SI, factors 1.00,
  initial 0,0, increment 0,1 (confirmed below). The settings actually in effect are read back
  and written to the record header.
- **No input means File > New.** r2x accepts the Quick Define defaults through the dialogs rather
  than shipping a copy of Newbeam, so the default follows the installed program (including an
  `r2k.r2k` template file, if one is present). The record is `newbeam.r2x.txt`, Response's name
  for a new section, in the current folder unless `--out` is given.
- **Detail views.** Every chart with a data export in four of Response's nine-chart views:
  General, Cracking, Reinforcement and No Shear, chosen with `--views` (default all). A chart that
  recurs in several views (Longitudinal Strain is in all four) is one section. Not captured: the
  Load Deformation Plot, a whole-member result whose curves are mostly per-stage maxima the
  toolbox can derive from `--stage all`; Mohr's Circles, deferred; and the charts that are
  pictures only (cross section, crack diagram, internal forces, N+M).
- **Stages.** Control charts always cover every stage; `--stage` selects the stages exported for
  the detail views. Stage 0 is the initial load. `peak` is the stage Response shows when the solve
  finishes. A stage number past the last stage is an error.
- **Report.** Optional, HTML, peak stage only: the summary screen as Response opens after solving,
  the control charts, and every detail-view chart as Response draws it (Copy Chart Picture) next
  to its data. Pictures rendered under Wine are checked by eye; they are not byte-comparable with
  Windows.
- **stdout.** `--stdout` writes the raw record only and creates no files. One input, no report.
  Progress and the spinner always go to stderr; the spinner shows only when stderr is a terminal.
- **Out of scope.** An input whose loading includes shear stops with a reason (exit status 3).

## `r2x solve --help`

```
usage: r2x solve [INPUT ...] [options]

Run a full sectional response in Response-2000 1.9.7 and capture the data
from its control charts and detail views.

Scope: axial load and moment. Not M-N interaction or full-member analysis.
r2x never edits the input file. Options override the input. Options you
leave out keep the input's value, or Response's start-up default if the
input has none.

Input:
  INPUT ...             .rsp or .r2t files; globs allowed (cases\*.r2t).
                        Default: a new Quick Define section (Newbeam).

Analysis:
  --units {si,us,kgcm}  Units for loads and results.
                        Default: input's, else si.
                          si     kN    kN·m    mm   MPa
                          us     kip   kip·ft  in   psi, ksi
                          kgcm   ton   ton·m   cm   kg/cm2, t/cm2
  --factors {none,csa}  Material reduction factors.
                        Default: input's, else none.
  --initial N,M         Initial load, in the units in effect.
                        Default: input's, else 0,0.
  --increment N,M       Load increment; only signs and ratio matter.
                        Default: input's, else 0,1.
                        N: tension positive. M: compression on top positive.

Output:
  --stage STAGES        Stages for the detail views: peak, all, or numbers
                        and ranges (0,10,20-30 or peak,0-5). 0 is the
                        initial load. Control charts always cover every
                        stage. Default: peak.
  --views VIEWS         Detail views: all, or any of general, cracking,
                        reinforcement, no-shear. Default: all.
  --report              Also write an HTML report of the peak stage.
                        Default: off.
  --out DIR             Folder for results. Default: next to each input.
  --stdout              Write the raw record to stdout and no files. One
                        input only; not with --report.
  --overwrite           Replace existing results. Default: stop.

Running:
  -p, --parallel N      Solve up to N inputs at once. Default: 1.
  -q, --quiet           Errors only. Default: off.

Results (NAME is the input file name, or newbeam without one):
  NAME.r2x.txt          Raw record: exported chart data, byte for byte, with
                        versions, input SHA-256 and the settings in effect.
  NAME.r2x.html         Report (--report only).

Exit status: 0 solved · 1 failed · 2 usage error · 3 out of scope

Examples:
  r2x solve
  r2x solve beam.r2t --report
  r2x solve beam.r2t --stage all
  r2x solve beam.r2t --views cracking,no-shear
  r2x solve col.rsp --units si --initial -2000,0 --increment 0,1
  r2x solve cases\*.r2t --out results --parallel 4
  r2x solve beam.r2t --stdout | py parse.py
```

`r2x health` is unchanged.

## Confirmed in Response-2000 on Windows

Checked by hand on 2026-10-25 (Phase 0). Screenshots are in Jamie's `_archive/phase0`; the
reference cases are in `tests/reference/`.

- **Units.** Options > Preferences ("Response-2000 Preferences") offers SI Metric, US Customary
  and kg/cm Metric, and a File Override checkbox, ticked by default. Loads are in kN and kNm,
  kips and kip-ft, or ton and ton-m; lengths in mm, in or cm; stress in MPa, psi (concrete) and
  ksi (steel), or kg/cm² (concrete) and t/cm² (steel). In exports, strain is mm/m in SI and ms
  (the same numbers) in US units; curvature is mrad/m in SI and rad/10³ in in US units.
- **Switching units converts everything in memory, loads included.** An increment of 1.00 kNm
  becomes 0.74 kip-ft, and 0.10 ton-m. So r2x sets units before loads, and `--initial` and
  `--increment` are in the units in effect. The Define Loading dialog shows two decimals, so
  loads read back from it are rounded to two decimals.
- **Material factors.** Concrete, Steel and Prestress fields, 1.00 meaning no factor. The CSA
  button sets 0.65, 0.85 and 0.90; None sets 1.00. With factors, the status bar says
  "(FACTORED)" and labels the loads Nf, Mf, Vf; chart titles do not change.
- **Loads > Sectional Loads** opens "Define Loading": rows Axial Load, Moment and Shear; columns
  Constant + Increment; units at the right. Shear is in the same dialog, so r2x can check it
  there before solving.
- **File > New.** Quick Define has four pages (title and materials; section shape; top and
  bottom bars; stirrups and tendons). Accepting every default gives exactly Newbeam: the saved
  file differs from `tests/reference/newbeam/input.r2t` only in its date. Start-up state: SI,
  factors 1.00, loads 0,0,0 + 0,1,0. There is no `r2k.r2k` template in the program folder.
- **What a file stores.** Save As writes the same XML whether it is named `.r2t` or `.rsp`. It
  stores non-default loads (`<sectloading BN="-2000.0"/>`, `MN`, `MM`), factors
  (`<analysisoptions phic="0.65" phis="0.85" phip="0.90"/>`) and units (`units="US"`, with every
  value converted and rounded to the displayed precision). The rounding makes a file saved in US
  units a slightly different section (Newbeam: 248.31 against 248.44 kip-ft at peak), so r2x
  switches units in memory and never by saving and reopening.
- **File Override.** Ticked, a file's units win when it is opened, and the preference switches
  to match; unticked, the preference wins. Factors come from the file either way. Response keeps
  no preferences between sessions (`Response.ini` holds only recent files), so every job starts
  in SI, factors 1.00, File Override ticked, and an input's stored settings stay in effect unless
  an option overrides them, as *Decisions* assumes.
- **Peak.** Response opens on the peak of the load being increased: the maximum moment for a
  moment increment (with or without a constant axial load), the largest compression for an
  axial-only increment.
- **Axial-only increment.** Both control charts are `Control : Axial Load - |e_x` (axial load
  against εx) and identical; there is no Moment–φ chart. Curvature is not zero when the
  reinforcement is unsymmetric, and the moment shows a small numerical value (−2.5 kNm for
  Newbeam) where it should be zero.
- **Copy Chart Picture** puts EnhancedMetafile and MetaFilePict on the clipboard; no bitmap.
- **Version.** The splash screen says 1.9.6 (beta); Help > About said 1.9.7. r2x identifies the
  program by `r2k.exe`'s SHA-256 rather than by either name.

How the implementation follows from this (Phase 3):

- Settings go through the Preferences page (dialog 320) and Define Loading (dialog 5), with
  control IDs from `r2k.exe`'s own resources (`tools/dialogs.py`, output in
  `docs/r2k-dialogs.txt`): units before loads, then every setting read back for the record
  header. Shear in Define Loading stops the job before solving (exit status 3).
- The control charts depend on the loading, so r2x reads their titles instead of expecting one
  pair (Moment–εx and Moment–φ, or Axial Load–εx in both places).
- Stage identification matches εx, the strain profile's value at y = 0, against the εx curve, and
  the curvature against the Moment–φ curve when there is one, with units from the axis titles
  (mrad/m with mm or cm, rad/10³ in with in). Both checks must agree.

Without an input (Phase 4), r2x starts Response with no file and opens the Quick Define wizard
with **Define > Quick Define**, then presses Next three times and Finish. On a fresh start that
is the wizard File > New shows; File > New's own command (24331) does not respond to a posted
message under Wine. The result matches a hand capture of File > New on Windows byte for byte
(`tests/reference/newbeam-filenew`). The section is Newbeam, but only its control curves are
byte-identical to opening `tests/reference/newbeam/input.r2t`: the detail views list the
reinforcement layers in another order and differ in the last digit of some depths. That is
Response's own difference between a section defined in memory and one read back from a file,
and it shows on Windows too. With an `r2k.r2k` template in the program
folder, Response loads it at start and the new section keeps the template's settings (with a
saved CSA file as the template, the factors are CSA); the record header has its SHA-256.

The report (Phase 5) is one self-contained HTML file, `NAME.r2x.html`, written next to the record
and before it, so the record still appears last. The worker builds it in the container
(`src/r2x/report.py`). Right after the solve, once the peak is identified and before any paging,
it takes:

- the main window as it is on screen (Wine's own drawing of it, title bar included);
- **Copy Chart Picture** of each control chart (once when both are the same chart, as with an
  axial-only increment) and of the five detail views. The picture is an enhanced metafile; the
  helper plays it into a bitmap 900 pixels wide, kept in the report as PNG.

Each chart's picture sits beside a table of its Copy Chart Data export at the peak, taken from the
record, with Response's own text in a collapsed block below it. The settings in effect and the
record header head and close the page. The record is the same bytes with or without `--report`
(`tests/test_worker_wine.py`). `--report` is not allowed with `--stdout`, and an existing report
needs `--overwrite` like an existing record; without `--report`, an existing report is left alone.

Under Wine the pictures need fonts that a bare image lacks: Wine's own (`fonts-wine`, which has
Symbol) and Arial's metrics (`fonts-liberation`). Response writes the Greek letters in chart titles
(εx, φ) in the Symbol font at codes Windows maps to U+F0xx; Wine's Symbol font has the glyphs but
not that map, so they showed as boxes. The prefix gets a copy of Wine's Symbol font with the map
added (`src/r2x/worker/prefix.py`). Pictures are checked by eye against Windows; they are not
byte-comparable.

## All detail views (0.2.0)

Found under Wine on 2026-10-26, with Newbeam at its peak; how r2x 0.2.0 follows from it.

- **The view list.** Response chooses the nine-chart view with a drop-down under "Nine Graphs",
  above the control charts, not from the toolbar or the View menu. It lists Cracking, General,
  Mohr's Circles, No Shear and Reinforcement, and opens on No Shear for an analysis without
  shear. r2x reads the list's items and selects one as a user would: it sets the selection and
  sends the change notification to the list's parent, as the drop-down itself does, so the reply
  comes once the new view's charts are in place. 135 exports copied straight after a switch
  matched those copied a second later.
- **The stage stays.** Changing the view keeps the load stage (checked at the peak and 20 stages
  below it), and paging works in any view. So r2x makes one pass through the stages and goes
  through the views at each one: the view on screen first, then the others in the catalogue's
  order, which is three switches per stage for four views. A switch takes about 50 ms.
- **Charts.** Every view has nine cells; those with a data export are in `src/r2x/views.json`
  with their titles and record keys, and the rest are pictures only. Charts recur: Longitudinal
  Strain is in all four views at the same place, Transverse Strain in General and Reinforcement,
  and the two longitudinal reinforcement stresses in Reinforcement and No Shear (at different
  places). A recurring chart exports the same bytes in every view; r2x checks that at every stage
  and keeps one section. The Longitudinal Strain check also shows that a switch left the stage
  alone. Mohr's Circles has five charts with data too (shear–εx, shear–γxy, f2–ε2, shear on
  crack–ε1, f1–ε1), deferred with the view.
- **Context menus.** A data chart's menu has Copy Chart Picture, Copy Chart Data, View Data,
  Properties, Auto/Max Range and Toggle Text (the top control chart's only the first three). A
  picture's menu is different: Cross Section's has Copy Picture and Toggle Fill, the Crack
  Diagram's adds Select Font, Toggle Mode and Select Widths. Its second item would toggle the fill
  instead of copying data, so before choosing Copy Chart Data r2x checks that the open menu is a
  data chart's. Every data chart's menu is as wide as its Copy Chart Picture item makes it (134
  pixels under Wine), and picture menus are narrower (102 to 125). The width is taken from a
  control chart in each run, so the check does not depend on fonts.
- **Record.** Format version 1 still: a new header key, `views`, and new sections, as
  `docs/raw-format.md` allows. With `--views no-shear` the sections are byte for byte and in order
  those r2x 0.1.0 wrote (`tests/test_worker_wine.py`).
- **Report.** One section per view: Response's window in that view, then each chart not already
  shown under an earlier view, picture beside data. Each window is taken after the view's chart
  pictures, and again until two in a row are the same, so a view is never caught half-drawn.
- **Time.** Newbeam with `--stage all`: 37 s for all four views (1,262 sections), 10 s for No
  Shear alone (0.1.0: 9.5 s), in the cloud environment.
