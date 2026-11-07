# Marshall.rsp: a shear peak that look-alike stages hide

**To capture** (first verification pass, `docs/risk-register.md`, S2 and S3). Response's own
example `Marshall.rsp`, as it is: an `.rsp` input, and a peak whose strain profile matches
five stages, so r2x pages from stage 0 to tell which it is. No reference on Windows covers that
path yet.

## Input

`Marshall.rsp` from Response's program folder (SHA-256 `dda664e1…ee89f17`). It is not
committed: it is part of Response, which r2x does not redistribute. The Wine test reads it from
the linked folder.

## Settings

None: the file's own (moment and shear increasing together, increment 0, −1, 1).

## Exports to capture

Open `Marshall.rsp`, **Solve → Sectional Response** without changing the stage, then the
routine in `../README.md`, *Adding a case*, steps 2 to 5, with every view (`capture.ps1` with no
`-Views`). The stage is the one Response opens on.

## What r2x gives under Wine (2026-11-07, r2x 0.5.0)

40 stages (0–39); Response opens on **stage 34**, the largest moment (V 476.4 kN, M −476.5 kNm,
curvature −5.670 mrad/m, γxy 5.158 on the top control curve), although its shear peaks at stage
36 by 0.07 kN. Shear–γxy on top, Moment–φ below. Its curvature matches stages 34, 35 and 37 to
39; r2x tells them apart by their exports, with a note.

## Capture

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response | 1.9.7, `r2k.exe` SHA-256 `bbf4bc59…4e74` |
| By | |
