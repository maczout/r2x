# Reference cases

Each case is a folder holding the input `.r2t` and exports produced by Response-2000 running
natively on Windows, laid out the same way as r2x output. These files are stored byte-for-byte
(see `.gitattributes`); never edit or re-save them.

Reference exports are copied **by hand** in the Response GUI, so they share no code with r2x.
`capture.ps1` only saves the clipboard to the right file name after each manual
**Copy Chart Data**; it does not touch Response.
