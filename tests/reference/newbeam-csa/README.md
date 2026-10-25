# Newbeam, CSA material factors

Newbeam (`input.r2t`, the same file as `../newbeam/input.r2t`) with the CSA material
resistance factors.

## Settings, applied by hand

**Options → Preferences → CSA** button: Concrete 0.65, Steel 0.85, Prestress 0.90. Units SI
Metric, File Override ticked (the defaults).

## Exports

Both control curves (Moment–εx and Moment–φ, 57 stages, 0–56) and the five No Shear charts at
the stage Response opens on after solving: the maximum factored moment, **stage 46**, identified
by curvature (20.726 mrad/m) and by εx at mid-depth (3.805 mm/m).

Status bar at that stage: "(FACTORED) Current Loads", Nf : −0.0 kN, Mf : 250.2 kNm,
Vf : 0.0 kN. The chart titles are the same as without factors.

## `saved.r2t`

Response's own **Save As** after applying the factors. It stores them as
`<analysisoptions phic="0.65" phis="0.85" phip="0.90" sustainM="-0.0"/>`, and reopening it
restores them whether or not File Override is ticked. Solving `saved.r2t` reproduces these
exports byte for byte (r2x 0.0.1 under Wine 9.0, 2026-10-25).

## Capture

The routine in `../README.md`, *Adding a case*.

| Captured | Notes |
|---|---|
| Date | October 25 2026 |
| Windows version | Windows 11 Pro |
| Response | `r2k.exe` SHA-256 `bbf4bc59…4e74` (see `../../docs/wine-spike.md`) |
| By | Jamie McIntyre |
