# History

Why r2x is as it is, and what was found in Response-2000 along the way, kept as it was written
at each version. Using r2x is in `docs/guide.md`; how it works now is in `docs/internals.md`.
Where these notes and those documents differ, the notes are history and the documents are
current. The Wine spike that came before 0.1.0 is in `docs/wine-spike.md`.

Versions: 0.1.0 (2026-10-25) the command line; 0.2.0 (2026-10-26) all detail views; 0.3.0
(2026-10-27) shear and More Detail; 0.4.0 (2026-11-07) defining a section and the session;
0.5.0 (2026-11-07) linking the user's own Response, and what came before setting r2x down.


## The command line (0.1.0)

**Status:** agreed 2026-10-25; implemented in full in r2x 0.1.0 (2026-10-25). `--views` added
in r2x 0.2.0 (2026-10-26). Shear, loads as N,M,V, `--more-detail` and the slimmer report in r2x
0.3.0 (2026-10-27), implemented ahead of the Windows reference captures. Phases 3 to 5, *All
detail views* and *Shear and More Detail* below record how. The help text, then agreed here, is
now in `docs/guide.md`, and `tests/test_cli.py` keeps them in step. `r2x define` and the session
(`r2x` alone) in r2x 0.4.0 (2026-10-28, under Wine; reviewed 2026-11-03): *Defining a
section*, at the end, and `docs/define.md` (since 0.5.0 split between `docs/internals.md`,
`docs/dialogs.md` and this file).

**Existing results** (decided 2026-11-03): as in Response, solves are cheap to re-run and their
results almost throwaway, so a solve replaces them, and a question to accept that is enough, as
Windows asks before Save As replaces a file. At a terminal `r2x solve` asks once (`[n]`: Enter
keeps them); `--overwrite` replaces them without asking; with no terminal to ask at (piped, a
script) it stops with a usage error, as before. In a session `solve` replaces the record and the
report beside the file without asking. Nothing checks whether a record is a solve of the file
as it is now; the record's header keeps the input's SHA-256 for anyone who needs to.

A stage number past the last stage is a usage error (exit status 2), found once the solve has
given the stage count. With several inputs, the exit status is the most serious outcome: 1, then
2, then 3.

### Decisions

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

### Confirmed in Response-2000 on Windows

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
is replaced as an existing record is (asked at a terminal, or `--overwrite`); without
`--report`, an existing report is left alone.

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

## Defining a section (0.4.0)

**Status:** released in r2x 0.4.0 (2026-11-07). Built under Wine on 2026-10-27/28 from the
plan (the Claude Doc "r2x define and the r2x session — plan", phases D0, D1 and D2), with
Jamie's review changes of 2026-10-28 built on 2026-11-03 (*Review changes*, below). On
Windows the smoke test, the report's reload and the three Quick Define reference cases passed
on 2026-10-28; after the review changes, on 2026-11-07, the five reference cases made by hand
(the three Quick Define ones, `add-delete` and `long-modify`) matched and a session was
smoke-tested again on the Framework.

Planned in the Claude Doc "r2x define and the r2x session — plan" (2026-10-27); built under
Wine on 2026-10-28. How a step works, every dialog's fields and what was found in Response are
in `docs/define.md` (since 0.5.0, `docs/internals.md` and `docs/dialogs.md`). The decisions:

- **`define` is always the verb, the part of the section the noun**, at the session's prompt
  and on the command line alike: `define quick`, `define long add web`. The nouns: `quick`,
  `general`, `materials`, `section`, `long`, `trans`, `tendons` (`add`, `modify` or `delete`,
  then the item's name, asked if left out), `loads`, `units`, `factors`.
- **Questions only.** A define asks its dialog's fields, in the dialog's order and words, each
  with the value the dialog shows now; Enter keeps it, and a field is set only when the answer
  differs. A field inside one of the dialog's frames is asked under the frame's text, printed
  once as a heading; choices are listed under their question. No options give a define's
  values: automation writes the input file elsewhere and hands it to `solve`. (Answers can be
  piped, one per line, which the tests use.)
- **Response checks the values**, and its own questions and messages are passed on in its
  words; r2x checks only that a number is a number and a choice one of the choices.
- **The file chain.** Each step is one container run: Response opens the file, one dialog is
  set, and Response saves the file back (Save As). r2x never reads or writes the XML.
- **The file is the section; arguments are the analysis.** `solve` takes `r2x solve`'s options
  for the session's file and never changes it. Loads, units and factors can go either way.
- **The report is the preview and the summary**: every step rewrites `NAME.r2x.html` with the
  input screen after Save As, and the page reloads itself. In a session `solve` always writes
  the report (with the outputs); `r2x solve` alone keeps it opt-in. A define after a solve takes
  the outputs out.
- **Beside a section** there are only `NAME.r2t`, its report and, once solved, its record.
  Repeated defines and solves overwrite them (*Existing results*, at the top).
- **Undo** is one step back, inside a session only; the copy is held by the session.
- **The date:** a new section gets today's date on the Windows side (Edit General's date);
  a way to set another comes later.
- **The file name** is asked by `define quick` in a session, defaulting to the session's file or
  to Response's title for a new section (`new-cross-section.r2t`).

```
usage: r2x define NOUN [ACTION [NAME]] FILE
r2x                     (a session: define, open, solve, undo, report, help, quit)
```

Exit status of `define`: 0 done (saved, or nothing changed), 1 failed (Response's message, or
the person stopped answering: nothing is saved), 2 usage error. `show`, `save` and `?` on a
question were dropped in the review (2026-11-03): the report is the summary, a define always
saves, and `[default]` says what Enter keeps.

### Why a file per step, and units first

**Why a file per step:** a section defined in memory exports slightly differently from the
same section read back from its file (found with File > New in 0.1.0): Response sorts the
longitudinal layers by depth when it opens a file, and keeps a section defined in memory in the
order they were added. A file opened and saved again keeps its bytes from then on. So after its
first step a section is always the file Response wrote, and anyone who opens it gets the same.

**Units first.** Quick Define's defaults follow the units in effect: in US units they are a
10 × 24 in beam with #6 and #8 bars, f'c 5000 psi. So `define quick` on an existing file opens
that file first (its units, through File Override), and in a session with no file yet,
`define units` is remembered for the `define quick` that follows. Switching units with
`define units` converts the section in memory as Preferences does, and the file is saved in
those units, with Response's rounding (found in 0.1.0).

### Response's own dialogs

| What Response shows | When | What r2x does |
|---|---|---|
| "Do you wish to create a new section?" (Yes/No) | Quick Define on an existing section | answers Yes: `define quick` always starts a new section |
| any other Yes/No message box | e.g. setting fy while Materials shows "Detailed" ("Changing this value will overwrite the detailed parameters"); Add with a name that exists; Modify with a new name | asks it, word for word, with no default answer |
| a message box with OK | a message | shows it, presses OK |
| **Reinforcement Types** (a list) | leaving a Quick Define page, or Add/Modify, with a bar designation Response does not know | asks for a bar from Response's list, printed under the question by name (not numbered: bar names such as 10 and 15 are numbers): its rows are the lines of `rebar.dat` in order, so the answer picks the row with that name. No default: Response's own Cancel quietly takes the first row (10M) |
| **View Data** ("Errors in defining Section ...") | after Finish, for errors Response has already fixed ("Negative width found ... Made positive") | shows the text; the section is as Response made it (the report's input screen shows it; undo in a session) |

Response checks little. Quick Define takes a negative f'c or width and makes it positive
(f'c −5 is saved as 5.0), and takes "abc" for f'c; r2x refuses anything that is not a number
before it reaches the dialog. Bars are the exception: an unknown designation brings up the list.

### Findings

Found under Wine on 2026-10-27 and 28, on Newbeam and on sections made with Quick Define.

- **Quick Define with every default gives Newbeam**: saved straight away, the file is
  `tests/reference/newbeam/input.r2t` byte for byte once the date is Newbeam's (the first
  test in `tests/test_define_wine.py`). It needs no File > New (24331, which does not answer
  a posted message under Wine): Define > Quick Define opens the same wizard.
- **Quick Define's derived values:** Response works out the bar layers (six 30M bars in a
  300 mm web become two layers, `bot3` and an unnamed one), `fu` (1.5 fy), the member length
  and the moment diagram. Those are Response's; r2x only answers its questions.
- **A file opened and saved sorts its layers**; opened and saved again it keeps its bytes.
  Adding a layer and deleting it again leaves the file byte for byte as it was before.
- **The order of a new section's layers is not reliable** (found with the Windows references,
  2026-10-28). Quick Define's T-beam and I-girder made by hand on Windows and by r2x hold the
  same layers with the same values, but the layer Quick Define splits off (`bot3`, the fourth
  strand layer) comes last in the hand-made file and first in r2x's. Opened and saved again by
  Response, the two are the same bytes, and they solve to the same record. Whether typing
  through the wizard or Windows against Wine makes the difference is not known; nothing after
  Response's first opening of the file sees it. So a reference case matches when its files are
  the same bytes, or else the same section with the layers in another order that solves to the
  same record (`tests/reference/define/compare.py`).
- **Modify takes every field as the dialog shows it**, as in the GUI: Newbeam's bottom layer
  at 63.90 shows as 64 (Dist. from Bottom has no decimals), so a modify that changes only its
  bar count stores z = 64.00. Quick Define's derived depths survive only until a layer is
  modified. Add uses the fields shown too; its defaults are the selected layer's.
- **Names:** Response lists the unnamed bottom layer as `bot` (and saves no `name` for it).
  Add with a name that exists asks whether to modify the existing layer, and then, since the
  layer selected is another, whether to overwrite it; answered No, Response adds the layer as
  `top1`, and r2x follows the name Response gave. Modify with a new name asks whether to
  overwrite the existing type; answered No, Response adds a new type beside the old one.
- **Materials:** with more than one rebar type of the same strength (Newbeam: Steel 1 and
  Trans), Basic Properties shows fy as "Detailed". Setting it asks to overwrite the detailed
  parameters; Yes merges every type into one, Steel 1 (Trans goes, and the stirrups use
  Steel 1). Enter leaves it alone.
- **Concrete Section** changes the shape only: the bars stay where they were.
- **Loads** are saved in `<sectloading>` as `BN`, `BM`, `BV` (constant) and `MN`, `MM`, `MV`
  (increment), each only when it differs from Response's default, as found in 0.3.0.
- **Title and comments** share Edit General's one box: the first line is the title, the
  others the comments, saved together in `name` (and in the member's material type). The main
  window's title then has a line break, which the helper now turns into a space.
- **Tendons** are `longreinfx` layers with a prestrain (`dep`); Define Tendons lists only
  those. Strand designations come from `rebar.dat` as bars do (S13, ...).
- **Quick Define and prestressing None:** the strands field stays enabled, labelled
  "Number of 13 mm strands".
- **A circular section** in Quick Define has 16 top bars and no bottom bars by default, and
  hoops.

### Frames

Response groups a dialog's fields in frames (group boxes), and a frame's text can carry the
meaning of the fields in it: Quick Define's third page has "Top Non-Prestressed Reinforcement"
and "Bottom Non-Prestressed Reinforcement" for a rectangle, T or I, but "Outer Non-Prestressed
Reinforcement Ring" and "Inner Non-Prestressed Reinforcement Ring" for a circle, around the
same controls. Before the review r2x put "Top, " and "Bottom, " before the labels from the
catalogue, so a circle read as linear layers (found by Jamie on Windows, 2026-10-28).

So a field's frame is read from the dialog as its question is asked, never fixed in the
catalogue: the worker lists the page's windows (`kids`, with their rectangles) and takes the
innermost visible Button with text whose rectangle encloses the field's control (a check box
or radio button encloses nothing). No change to the helper was needed. A frame whose text only
repeats the question (Preferences' "Units" around the units) is left out. The command line
prints a frame's text once, as a heading over its questions; the `set:` line groups the fields
it read back the same way. The catalogue's own question words leave out the frame's (Number of
Bars, not Top, Number of Bars; Concrete under Material Factors). Define Loading has no frames;
its questions keep their own words (Axial Load, Constant).

### The report reloads itself

A define step rewrites the section's report, the same `NAME.r2x.html` that `solve --report`
writes, with the inputs only: Response's input screen after Save As, which is the section as
the file now holds it (decided 2026-10-28: the dialog pictures, nested dialogs or only the last
one set, did not communicate). A define after a solve so takes the outputs out; a solve in a
session writes it whole again. A solve's report keeps its Preferences and Define Loading
pictures (decided 2026-11-03): those are the analysis settings, re-set on every solve as its
arguments, and the material factors' values show nowhere else.

Every report reloads itself when r2x rewrites it, with no server and no files besides it. A
page opened from disk (`file://`) cannot read files, but it can frame one and be posted to by
it: every 1.5 s it loads itself, hidden, in a frame; that copy posts its stamp (a hash of the
page, at the top) to the page and stops loading there (`window.stop()`). A different stamp
means the file has changed: the page reloads, which keeps the place on it. Checked in
Chromium from `file://` (scroll position kept), and on the Framework (2026-10-28). The
pictures are inside the page, as before.

### Time per step

Under Wine in the cloud environment, the worker's time (Response starting, the dialog, Save
As, the input screen's picture; the container adds about a second on the Framework). Measured
with four dialog pictures per Quick Define before 2026-11-03; a step now takes one picture.

| Step | Seconds |
|---|---|
| `define quick`, Enter throughout (four pages) | 4.2 to 6.5 |
| `define quick` with answers on every page | 5.4 to 7.2 |
| `define general`, `section`, `loads`, `units`, `factors` | 2.7 to 3.3 |
| `define long add`, `delete`; `tendons add` | 3.2 to 3.9 |
| a step with one of Response's questions (`materials` fy, `trans` rename) | 4.1 to 5.2 |

### Decisions taken in building it

Confirmed by Jamie on 2026-11-03 ("good enough for now"); the plan's settled points are kept as
they were:

- **The file name is asked by every `define quick` in a session**, defaulting to the
  session's file (or `new-cross-section.r2t`, from Response's title for a new section); the
  plan has it asked by the first define only. A file that exists, other than the session's,
  is replaced only after a yes; on the command line, `r2x define quick FILE` asks the same
  when FILE exists.
- **`define units` with no section yet** is remembered for the next `define quick` (units
  only: factors do not change Quick Define's defaults). Other defines need a section.
- **`undo`** (one level) puts back the file from before the last step and rewrites the report with its
  input screen; a step that made a new file has nothing to put back (the file stays, and the
  session goes back to its file before).
- **The report opens in the browser** the first time a session writes it (only at a
  terminal); `report` opens it again.
- **Answers can be piped**, one per line (Enter: an empty line); at the end of the input
  every question is answered with Enter, and a question that needs an answer stops the step.
  The tests and `tests/reference/define/check.ps1` use this; it is not meant as an
  automation interface (that is a script that writes the input file).
- **Response's View Data errors after Finish** are shown, not asked again: the wizard has
  closed, and the section is as Response made it.

### Review changes (Jamie's review of 2026-10-28, decided 2026-11-03)

- **The report's inputs are the input screen only** (above, *The report reloads itself*).
- **Frames are headings.** A field's frame text is read from the dialog as the question is
  asked (*Frames*, below) and printed once, as a heading over that frame's questions, which
  are indented under it; not again when a question is asked again after a wrong answer.
- **Choices print under their question**, numbered, and the answer is typed on the line after
  them (`> `), so they cannot read as the previous question's.
- **No `?`** on a question: it only restated the default, and `[default]` says that.
- **No `save`**: a successful define always saves the file; to save it under another name,
  copy it in the shell. `open FILE` stays.
- **No `show`**, in the session or as `r2x show`: the report is the section's summary. With
  it goes the check of whether the record is a solve of the file as it is now; there is none
  anywhere. As in Response, settings are light and solves cheap to re-run, almost throwaway:
  repeated defines and solves overwrite the file, its report and its record, and a prompt to
  accept an overwrite is enough. In a session nothing asks (the session's file is the one being
  worked on, as with Save in Response); `define quick` asks before replacing another file;
  `r2x solve` asks at a terminal before replacing results (`--overwrite`: without asking; no
  terminal: it stops). The record keeps its input SHA-256 in the header.
- **The object is the section or the file**, not Response's menus: the nouns' descriptions say
  what they set (`long`: longitudinal reinforcement layers), and the help, the banner and the
  README follow. The questions keep Response's own field labels.

### Not done (later, each planned on its own)

Materials' Detailed pages and Rebar Details; circular and distributed bar patterns; standard
and user-defined shapes; shrinkage and thermal strains; a live container if steps feel slow; a
file with several sections (Response asks which to load: r2x stops with its question).

### Reference cases

`tests/reference/define`: thirteen cases, each made by hand in Response on Windows
(`hand.r2t`, steps in its `README.md`) and by r2x from the same answers (`session.txt`, an r2x
session). `check.ps1` runs them on Windows and compares; `tests/test_define_cases_wine.py`
does the same under Wine. `cases.json` holds the answers by field, and
`tools/define_cases.py` writes each case's `session.txt` and `README.md` from it. The three
Quick Define cases are compared but for the date.

## Linking and parking (0.5.0)

**Decided 2026-10-28:** finish a short list of work, then set r2x down and move on: an
interface review for structural engineers, documentation by reader, a consistent disclaimer, a
first pass of systematic verification (completed in the clone project, where it matters most),
and parking. r2x is good enough on speed; running fast and reliably in the long term goes
through a clone. Users link their own copy of Response; r2x does not bundle it.

**Decided 2026-11-07** (Jamie's review of Claude's proposals):

- **The image is published** on GitHub's registry (`ghcr.io/maczout/r2x:VERSION`), pushed from
  the Framework after it has been checked there, so the image users pull is the one checked.
  It doubles as insurance against a rebuild drifting.
- **Another build of `r2k.exe` is refused**, at `r2x setup` and on every run, unless linked
  with `--allow-unverified`; every record then says `response-verified: no`.
- **The report after a solve:** a page cannot bring its own window forward, so the guide says
  to put the terminal and the browser side by side, and a page that reloads out of sight flags
  its title (`● Solved`, `● Updated`) until it is looked at.
- **The first verification pass:** a risk register (`docs/risk-register.md`), a few hand
  captures on Windows aimed at errors the engineer cannot see, and a small prototype of checks
  on records alone; the eight define cases not yet made cut to a few short ones; no comparison
  of r2x's worker on Windows against Wine.
- Taken as proposed: `r2x setup --response FOLDER` with an environment variable to override
  it; one disclaimer kept in the code and shown in the help, `r2x health`, the session's
  banner, the report and the record header; the documents split by reader.

**Built and found, 2026-11-07:**

- **Only the files Response reads** (`.exe`, `.dll`, `.dat`, `.dtd`, `.r2k`) are hashed and
  copied into each job, not the whole program folder: Jamie's folder has `Response.ini`
  (Response's recent-files list, rewritten by every session on Windows) and a `Newbeam.r2t`
  edited after installing, which would change a whole-folder hash with ordinary use. The Wine
  suite passes from such a copy, byte for byte. `shape.dat`, the standard shapes, is a live
  input as `rebar.dat` is.
- **Going back a question** (`<`): within a page the worker asks the previous field again as
  the dialog now shows it; at the first question of a Quick Define page it presses the
  wizard's Back and starts at that page's last question. Going back to the shape on page 2,
  changing it and answering page 3 again gives the same file, byte for byte, as answering
  straight; so does going back within a page. Response's own questions cannot be gone back
  from: they are asked again.
- **What the input screen shows** is more than the earlier notes said: a tendon's prestrain
  (`Δεp = 6.50 mm/m`), crack spacing when set, and a moment axis away from the centroid are all
  on it. Bar and tendon depths as numbers, a tendon's slope and the material factors are not
  (`docs/risk-register.md`, *What the report leaves out*).
- **In the cloud environment** Docker Hub and PyPI cannot be reached from a build, so the
  image was checked there on an Ubuntu 24.04 base made with `debootstrap` and with wheels
  fetched beforehand: `r2x setup`, `r2x health`, a solve (Newbeam's 23 reference exports at
  the peak, byte for byte, 7.3 s) and a define step, through the real command line and
  docker. The Framework's build is the one released.
