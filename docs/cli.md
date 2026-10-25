# Command line

**Status:** agreed 2026-10-25. Implemented: the raw record (`docs/raw-format.md`), `--stage`,
`--out`, `--stdout`, `--overwrite`, `--parallel`, `--quiet`, the exit statuses, and `--units`,
`--factors`, `--initial` and `--increment` through Response's dialogs, and solving without an
input. Not yet: `--report`; r2x accepts it but stops with a usage error. `r2x solve --help`
matches the text below plus two notes, and `tests/test_cli.py` keeps them in step.

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
message under Wine. The section is Newbeam: its control curves are byte-identical to opening
`tests/reference/newbeam/input.r2t`. Its detail views are not: they list the reinforcement
layers in another order and differ in the last digit of some depths, as a section defined in
memory differs from one read back from a file. With an `r2k.r2k` template in the program
folder, Response loads it at start and the new section keeps the template's settings (with a
saved CSA file as the template, the factors are CSA); the record header has its SHA-256.
