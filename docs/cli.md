# Command line

**Status:** agreed 2026-10-25, not yet implemented. The README describes what r2x does today.

## Decisions

- **r2x is a kernel.** It drives Response-2000 and returns Response's own exports. Parsing them
  into a structured schema belongs to the wider toolbox (r2k), so r2x does not have to change as
  that schema evolves, and a real clone can later replace the wrapper behind the same schema.
- **The raw record is the result.** One text file per input. Each section is Response's Copy
  Chart Data text, byte for byte, behind a header with the versions, the input's SHA-256 and the
  settings in effect. Its layout gets its own document (`docs/raw-format.md`, to write) and a
  version number, since it is the kernel's contract.
- **Settings go through Response's dialogs only.** r2x never edits the input file, so it does not
  depend on the input format (`.rsp`, XML `.r2t`, or the older Ver_0.8 text `.r2t`).
- **Options are overrides.** An option that is left out keeps the input's value. If the input has
  none, it takes Response's start-up default, i.e. what File > New gives (expected: SI, no
  factors, initial 0,0, increment 0,1; to confirm). The settings actually in effect are read back
  and written to the record header.
- **No input means File > New.** r2x accepts the Quick Define defaults through the dialogs rather
  than shipping a copy of Newbeam, so the default follows the installed program (including an
  `r2k.r2k` template file, if one is present).
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
                          kgcm   t     t·m     cm   kg/cm2
  --factors {none,csa}  Material reduction factors.
                        Default: input's, else none.
  --initial N,M         Initial load. Default: input's, else 0,0.
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

Results (NAME is the input file name):
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

## To confirm in Response-2000 1.9.7 before implementing

The help text was written from the version-0.8-era manual (Bentz 2000, Appendix A).

- Options > Preferences: the names of the three unit systems, their force, moment, length and
  stress units (the `us` and `kgcm` rows above are unverified), and the material-factor fields
  and CSA button.
- Loads > Sectional Loads: the layout of the initial and increment columns.
- File > New: the start-up defaults listed under *Decisions*, and whether the program folder has
  an `r2k.r2k` template.
- Whether units and material factors are saved in `.rsp` and `.r2t` files.
- Which stage Response shows after solving an axial-only increment (is it still "peak"?).
- The clipboard format of Copy Chart Picture (bitmap or metafile).
