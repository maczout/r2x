# Command line

**Status:** agreed 2026-10-25; implemented in full in r2x 0.1.0 (2026-10-25). `--views` added
in r2x 0.2.0 (2026-10-26). Shear, loads as N,M,V, `--more-detail` and the slimmer report in r2x
0.3.0 (2026-10-27), implemented ahead of the Windows reference captures. Phases 3 to 5, *All
detail views* and *Shear and More Detail* below record how. `r2x solve --help` matches the text
below plus one note, and `tests/test_cli.py` keeps them in step.

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
  initial 0,0,0, increment 0,1,0 (confirmed below). The settings actually in effect are read
  back and written to the record header.
- **Loads are N,M,V** (0.3.0), as the Define Loading dialog has them: `--initial` and
  `--increment` take three values, and two are a usage error that says to add V. Any loading
  Define Loading accepts is in scope, shear included, constant or increment. An increment of
  0,0,0 solves the initial load alone.
- **No input means File > New.** r2x accepts the Quick Define defaults through the dialogs rather
  than shipping a copy of Newbeam, so the default follows the installed program (including an
  `r2k.r2k` template file, if one is present). The record is `newbeam.r2x.txt`, Response's name
  for a new section, in the current folder unless `--out` is given.
- **Detail views.** Every chart with a data export in four of Response's nine-chart views:
  General, Cracking, Reinforcement and No Shear, chosen with `--views` (default all), with or
  without shear: no pruning of charts that only mean something with shear; interpreting them is
  the toolbox's job. A chart that recurs in several views (Longitudinal Strain is in all four) is
  one section. Not captured: the Load Deformation Plot, a whole-member result whose curves are
  mostly per-stage maxima the toolbox can derive from `--stage all`; Mohr's Circles (Won't,
  decided 2026-10-27); and the charts that are pictures only (cross section, crack diagram,
  internal forces, N+M).
- **Stages.** Control charts always cover every stage; `--stage` selects the stages exported for
  the detail views. Stage 0 is the initial load. `peak` is the stage Response shows when the solve
  finishes (after any More Detail). A stage number past the last stage is an error.
- **More Detail** (0.3.0). `--more-detail N` presses Solve > More Detail N times after Sectional
  Response; `max` presses until Response refines no further. Past Response's limit r2x applies
  what it can and says so in a note; the record header's `more-detail` is the number of presses
  that took effect. Stage numbers, `--stage` and the stage count all refer to the refined solve.
- **Report.** Optional, HTML, for checking by eye that Response was driven as intended
  (slimmed in 0.3.0): screenshots only, under **Inputs** (Response's window before solving,
  Preferences and Define Loading as r2x leaves them) and **Outputs** (Response's window in each
  captured view at the peak), with a left-column index. No data, which is in the record.
  Screenshots are taken under Wine; they are not byte-comparable with Windows.
- **stdout.** `--stdout` writes the raw record only and creates no files. One input, no report.
  Progress and the spinner always go to stderr; the spinner shows only when stderr is a terminal.
- **Out of scope.** Exit status 3 is reserved for an analysis r2x does not cover; since 0.3.0
  nothing triggers it (until then, any loading with shear did).

## `r2x solve --help`

```
usage: r2x solve [INPUT ...] [options]

Run a full sectional response in Response-2000 1.9.7 and capture the data
from its control charts and detail views.

Scope: axial load, moment and shear. Not interaction diagrams or member
response.
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
  --initial N,M,V       Initial load, in the units in effect.
                        Default: input's, else 0,0,0.
  --increment N,M,V     Load increment; only signs and ratio matter.
                        0,0,0 solves the initial load alone.
                        Default: input's, else 0,1,0.
                        N: tension positive. M: compression on top positive.
  --more-detail N       Refine the solve with Solve > More Detail, N times,
                        or max: until Response refines no further.
                        Default: 0.

Output:
  --stage STAGES        Stages for the detail views: peak, all, or numbers
                        and ranges (0,10,20-30 or peak,0-5). 0 is the
                        initial load. Control charts always cover every
                        stage. Default: peak.
  --views VIEWS         Detail views: all, or any of general, cracking,
                        reinforcement, no-shear. Default: all.
  --report              Also write an HTML report: screenshots of the
                        inputs and of the peak stage. Default: off.
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
  r2x solve beam.r2t --increment 0,1,1 --more-detail 2
  r2x solve col.rsp --units si --initial -2000,0,0 --increment 0,1,0
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
  header. Shear in Define Loading stopped the job before solving (exit status 3) until 0.3.0.
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

The report (Phase 5, as it was until 0.3.0 slimmed it: *Shear and More Detail*, below) is one
self-contained HTML file, `NAME.r2x.html`, written next to the record
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
- **Checked on Windows** (2026-10-26). All four views' 21 charts, captured by hand at stage 56
  and at stage 36 (`tests/reference/newbeam`), match r2x's record byte for byte. The report
  matched Response by eye, and the Framework's container wrote the same record as the cloud's.

## Shear and More Detail (0.3.0)

Found under Wine on 2026-10-27 (Step 1 of the 0.3.0 plan), with Newbeam under several loadings,
a T-section variant of it, and Response's own examples (Marshall, se100am69, dm-n1n, Liping LB1);
how r2x 0.3.0 follows from it. Checked on Windows on 2026-10-27 with three hand-captured cases
(last bullet).

- **Control charts** depend on the increment, not on the constant loads:

  | Increment | Top | Bottom |
  |---|---|---|
  | V and M (N constant or none) | Shear–γxy | Moment–φ |
  | V and N | Shear–γxy | Axial Load–εx |
  | V alone | Shear–γxy | Shear–εx |
  | M, no V; or 0,0,0 | Moment–εx | Moment–φ |
  | N alone | Axial Load–εx | Axial Load–εx |

  A constant V with a moment increment gives Moment–εx and Moment–φ, as without shear. New record
  sections: `control/shear_gxy` (`Control : Shear - |g_x_y`, Shear Strain (mm/m) against Shear
  (kN)) and `control/shear_ex` (`Control : Shear - |e_x`). An increment with all three of N, M
  and V was not tried; r2x reads the titles, so it needs no table.
- **Views.** With shear anywhere in the loading Response opens on General (No Shear otherwise),
  and lists the same five views. Every catalogued chart is in the same cell and exports under
  the same title, so `src/r2x/views.json` is unchanged.
- **The stage Response opens on** is the peak of the bottom control chart's load: the largest
  moment when the increment has one, the largest shear for V alone. Marshall opens on stage 34,
  its largest moment, although its shear peaks at stage 36, by 0.07 kN. As before, `peak` is the
  stage on screen.
- **Shear–γxy is no stage key.** Its γxy is the average shear strain weighted by shear force,
  ∫ τ γxy b dy / ∫ τ b dy (the denominator is V): worked out from the Shear Strain and Shear
  Stress exports it matches the curve within 0.003 mm/m at every stage, for Newbeam and for a
  T-section, but only with the section's width b at each depth, which no export carries.
  Unweighted, it is about 20 % off for the T-section.
- **εx and curvature still work**, from Longitudinal Strain as before: curvature against
  Moment–φ, εx against Shear–εx or Axial Load–εx. With shear there is one of them, not two, and
  one is often not enough near and after a shear peak, where curvature hardly changes: Marshall's
  peak matches stages 34, 35 and 37 to 39; Newbeam at M/V = 1.8 m, 93 and 94; a constant
  N = −2000 kN with V alone, every stage from 7 to 23. With V alone εx is 0 until the section
  cracks, so Longitudinal Strain is the same bytes at stages 1 to 9.
- So r2x 0.3.0 **tells stages apart by their exports**. With Shear–γxy on top, or two stages with
  the same control points (an increment of 0,0,0), it reads the General view's Shear Strain
  beside Longitudinal Strain at every stage, which changes from each stage to the next; Shear
  Strain is recorded only if General is among `--views`. If the stage on screen matches several
  stages, r2x pages from stage 0 to the highest of them, checking every step against the control
  curves, and the stage on screen is the one whose exports are the same bytes; a note says so
  (Marshall: 12 s at the peak, against about 6 s without the extra pass). It stops rather than
  guess if none or several are.
- **When a solve has finished.** Shear solves were quick: 1 to 3 s for every case (36 to 95
  stages), new points up to about 0.5 s apart. Nothing visible marks the end (title and window texts
  stay; the status bar is OWL's own drawing, with no window text), but Response's process uses
  60 to 80 % of a processor while it solves and 0 to 4 % idle (read from `/proc` on the Linux
  side, with r2x copying a chart twice a second). r2x 0.3.0: finished once the bottom control
  curve has not changed for 1 s **and** Response's process used under 10 % of a processor over
  0.2 s; it fails after 300 s without a new stage (300 s in all before). The status line shows
  the stages solved so far.
- **How a shear solve ends.** Every case ended without a message: Response stops adding stages
  (Newbeam at M/V = 1 m: 201.5 kN at stage 30, then 12 more stages down to 48.6 kN). A section
  that fails under the initial load shows "Could not Solve for initial case. Lower Initial
  loads, or lower prestress", and r2x fails with that message (exit status 1), as before.
- **An increment of 0,0,0** gives two control points, both the initial load, and Response opens
  on the second (stage 1). Their Longitudinal Strain exports are the same bytes, their Shear
  Strain exports are not (stage 0's has an envelope series), so paging tells them apart.
- **More Detail** puts a new stage between every two stages up to the peak, and none after it.
  Existing points keep their export lines, byte for byte and in order: Newbeam goes from 60 to
  116, 228 and 327 stages, its peak from 56 to 112, 224 and 323.
- **Its limit is a number of stages, not of presses**: every case stopped at 327 stages (Newbeam
  after 3 presses, Newbeam at M/V = 1 m and Liping after 4, V alone after 5), the last press
  adding fewer. A press past it does nothing visible: no message, and the curves stay the same,
  which is how r2x tells. On Windows the menu item is greyed out once the limit is reached
  (Newbeam, after the third press); r2x posts the command without opening the menu, and a
  disabled command does nothing, so the outcome is the same.
- **The stage on screen stays the peak**, which can move to a new stage: Liping's fourth press
  moved it from stage 256 (246.48 kN·m) to 322 (246.65 kN·m), a new stage beside it.
- **Time.** A press takes 0.3 to 1.2 s; the finish signal covers it. Newbeam with an increment of
  0,1,1, all four views: 5.6 s at the peak and 37 s with `--stage all` (43 stages, 905
  sections); with `--more-detail max` (4 presses, 327 stages), 18 s.
- **Report.** Inputs: Response's window before solving, which summarises the section, the
  materials and the loads with r2x's settings applied, then Preferences and Define Loading as
  r2x leaves them. Define > Material Properties is left out: the input screen already shows f'c,
  fy and fpu, and its Materials Page needs a second tab for the bars. Outputs: Response's window
  in each captured view at the peak; the control charts are in every one. Without the per-chart
  Copy Chart Picture, Newbeam with `--report` at the peak takes 9.7 s in the cloud.
- **On Windows** (2026-10-27, Response 1.9.7 on Windows 11): `tests/reference/newbeam-shear`
  (0,1,1; every view at the peak, stage 30, and at stage 20), `newbeam-shear-only` (0,0,1; every
  view at the peak, 16) and `newbeam-moredetail` (More Detail twice; every view at the peak,
  224). The control charts, stage counts, peaks, opening view and status bars are as found under
  Wine, and so is every export byte for byte, with one exception: at `newbeam-shear`'s stage 20,
  one value that prints as zero has the opposite sign in each of Shear Strain (`-0.0000` under
  Wine at −274.35 mm) and Shear Stress (`-0.0000` on Windows at −300 mm), floating-point noise
  near the bottom of the section where shear is nil. The peak itself matches exactly, and
  solving the same input twice under Wine gives the same bytes, so the noise is Wine's against
  Windows', not run to run. r2x returns Response's bytes as they are; the Wine tests allow a
  signed zero in those two exports only. Response's Save As stores the load increments in
  `<sectloading>` as `MN` (axial), `MM` (moment) and `MV` (shear), each only when it differs
  from the default (0, 1 and 0); solving the saved files reproduces the captures.
