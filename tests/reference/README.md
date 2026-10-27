# Reference cases

Each case is a folder holding the input `.r2t` and exports produced by Response-2000 running
natively on Windows: `control/` for the control charts, `stages/NNN/` for the detail views'
charts at stage NNN, one file per record key (`docs/raw-format.md`). Every case has the five No
Shear charts at its peak; `newbeam` is to have every view's (see its README). These files are stored byte-for-byte (see `.gitattributes`); never edit or re-save
them.

| Case | Settings applied by hand | Peak stage | `saved.r2t` reproduces it |
|---|---|---|---|
| `newbeam` | none (moment only) | 56 of 0–59 | (no `saved.r2t`; `input.r2t` does) |
| `newbeam-axial` | constant N −2000 kN, moment increment | 37 of 0–45 | yes |
| `newbeam-axial-only` | axial increment only | 22 of 0–34 | yes |
| `newbeam-csa` | CSA material factors | 46 of 0–56 | yes |
| `newbeam-us` | US Customary units | 56 of 0–59 | no: values rounded on save |
| `newbeam-filenew` | no input: File > New, Quick Define's defaults | 56 of 0–59 | (no input file) |

Cases with settings keep `input.r2t` as given and say in their README how the settings were
applied. `saved.r2t`, where present, is Response's own Save As after applying them.

Reference exports are copied **by hand** in the Response GUI, so they share no code with r2x.
`capture.ps1` only saves the clipboard to the right file name after each manual
**Copy Chart Data**; it does not touch Response. It takes the views and their charts from r2x's
catalogue (`src/r2x/views.json`), checks each detail chart's title, and keeps files that are
already there, so it can be rerun to fill gaps.

## Adding a case

1. Make a folder here named for the case (e.g. `newbeam-us`) and copy the input into it as
   `input.r2t` (or `input.rsp`).
2. In Response on Windows: open that input, apply the case's settings through the dialogs,
   **Save As** `saved.r2t` somewhere outside the case folder, and run **Solve → Sectional
   Response** without changing the load stage. Screenshot the window, status bar included.
3. From **inside** the case folder (the script writes to the current folder):
   `powershell -ExecutionPolicy Bypass -File ..\capture.ps1`. It asks for both control charts,
   then for each detail view in turn: when it says, switch Response's view list (under "Nine
   Graphs", above the control charts) to that view, then copy each chart it names. It asks again
   if the clipboard is not new chart data, or not the chart it named. `-Views no-shear` (or a
   list, `-Views no-shear,cracking`) limits it to those views. PgUp and PgDn page the stage even
   right after using the view list.
4. Detail views land in `stages\peak`. That folder is renamed to the stage number (e.g.
   `stages\056`) once the Longitudinal Strain export has been matched to the control curves:
   by curvature against Moment–φ (mind the units), and by εx, the strain at mid-depth.
5. Write the case's `README.md`: what the case is, the settings applied and how, the status bar
   at the captured stage, and the capture details (date, Windows and Response versions, by whom).
