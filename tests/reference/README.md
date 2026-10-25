# Reference cases

Each case is a folder holding the input `.r2t` and exports produced by Response-2000 running
natively on Windows, laid out the same way as r2x output. These files are stored byte-for-byte
(see `.gitattributes`); never edit or re-save them.

Reference exports are copied **by hand** in the Response GUI, so they share no code with r2x.
`capture.ps1` only saves the clipboard to the right file name after each manual
**Copy Chart Data**; it does not touch Response.

## Adding a case

1. Make a folder here named for the case (e.g. `newbeam-us`) and copy the input into it as
   `input.r2t` (or `input.rsp`).
2. In Response on Windows: open that input, apply the case's settings through the dialogs, and
   run **Solve → Sectional Response** without changing the load stage. Note the status bar.
3. From the case folder: `powershell -ExecutionPolicy Bypass -File ..\capture.ps1`, then copy
   each chart it names. It asks again if the clipboard is not new chart data. Check each saved
   line shows the title you expect.
4. Detail views land in `stages\peak`. That folder is renamed to the stage number (e.g.
   `stages\056`) once its curvature has been matched to the Moment–φ curve.
5. Write the case's `README.md`: what the case is, the settings applied and how, the status bar
   at the captured stage, and the capture details (date, Windows and Response versions, by whom).
