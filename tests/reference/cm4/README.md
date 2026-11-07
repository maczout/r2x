# Cm4.rsp: a stage far below the peak

**To capture** (first verification pass, `docs/risk-register.md`, S2 and S7). Response's own
example `Cm4.rsp`: an `.rsp` input with a negative moment increment and 101 stages, captured at
its peak and at a stage far below it, to check r2x's paging over a long way.

## Input

`Cm4.rsp` from Response's program folder (SHA-256 `29817b2c…68582eb3`). It is not committed:
it is part of Response. The Wine test reads it from the linked folder.

## Settings

None: the file's own (increment 0, −1100, 0: moment alone, negative).

## Exports to capture

Open `Cm4.rsp`, **Solve → Sectional Response**, then the routine in `../README.md`, *Adding a
case*, with every view, for the stage Response opens on. Then **PgDn 38 times** and
`capture.ps1 -Stage peak-38` (every view again) for stage 20.

## What r2x gives under Wine (2026-11-07, r2x 0.5.0)

101 stages (0–100), Moment–εx on top and Moment–φ below. Response opens on **stage 58**,
the largest moment: M −2131.6 kNm, curvature −46.026 mrad/m, εx 18.31 mm/m. **Stage 20**:
M −1616.9 kNm, curvature −3.283 mrad/m, εx 0.618 mm/m.

## Capture

| Captured | Notes |
|---|---|
| Date | |
| Windows version | |
| Response | 1.9.7, `r2k.exe` SHA-256 `bbf4bc59…4e74` |
| By | |
