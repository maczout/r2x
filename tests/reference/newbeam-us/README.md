# Newbeam, US Customary units

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`, which is in SI) displayed and
exported in US Customary units.

## Settings, applied by hand

Open `input.r2t`, then **Options → Preferences → US Customary** (File Override ticked, the
default). Response converts the section in memory; nothing is saved and reopened.

## Exports

Both control curves (Moment–εx and Moment–φ, 60 stages, 0–59) and the five No Shear charts at
the stage Response opens on after solving: the maximum moment, **stage 56**, the same stage as
SI Newbeam. Units in the exports: moment kip-ft, depth in, strain ms (millistrain, the same
numbers as mm/m), curvature rad/10³ in, stress ksi (steel) and psi (concrete).

The stage was identified by εx at mid-depth (7.7869 ms, as in SI) and by curvature
(1.026 rad/10³ in). The curvature check in r2x 0.0.1 assumes SI units and does not find it.

Status bar at that stage: N : −0.0 kips, M : 248.4 kip-ft (336.8 kNm), V : 0.0 kips.

## `saved.r2t`

Response's own **Save As** in US units: `units="US"`, with every value converted and rounded to
the precision Response displays (250 mm becomes 9.84 in, 249.9 mm). That makes it a slightly
different section: solving it gives a peak of 248.31 kip-ft against 248.44 here, and 59 of the 60
curve points differ in the last digit. It is kept as an example of an input saved in US units,
not as a check of these exports.

## Capture

The routine in `../README.md`, *Adding a case*.

| Captured | Notes |
|---|---|
| Date | October 25 2026 |
| Windows version | Windows 11 Pro |
| Response | `r2k.exe` SHA-256 `bbf4bc59…4e74` (see `../../docs/wine-spike.md`) |
| By | Jamie McIntyre |
