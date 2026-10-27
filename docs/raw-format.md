# Raw record format

**Version 1.** This is r2x's contract: the wider toolbox reads it, so it changes only as
described under *Versioning*.

The raw record is the result of one solve: `NAME.r2x.txt`, or the bytes `--stdout` writes. It
holds Response-2000's own Copy Chart Data text, byte for byte, behind a short header that says
where it came from.

## Reading a record

Read it as **bytes**. Section lengths count bytes, and text mode (which rewrites line endings)
breaks them. In Python, with no dependencies beyond r2x itself:

```python
from r2x import record

rec = record.read("Newbeam.r2x.txt")             # or record.decode(sys.stdin.buffer.read())
rec.header["peak-stage"]                         # '56'
rec.control("moment_phi")                        # bytes of the Moment-φ export
rec.stage(56, "longitudinal_strain")             # bytes of one detail-view chart's export
rec.stages()                                     # [56]
```

Don't open a record in an editor and save it: an editor that changes line endings or encoding
breaks the lengths, and `record.read` then refuses the file.

## Layout

```
r2x-raw 1                                    format name and version
r2x-version: 0.3.0                           header: one "key: value" per line
response-exe-sha256: bbf4bc59…
…
units: si
…
views: general,cracking,reinforcement,no-shear
…
detail-stages: 56
                                             empty line: end of header
section control/moment_ex 1635               section NAME LENGTH
  Data from Graph                            LENGTH bytes of Response's export…
  …
                                             …then CRLF
section control/moment_phi 1644
…
end                                          end of record
```

- Every line r2x writes ends in CRLF, as Response's export text does, so the file has a single
  line-ending style throughout.
- First line: `r2x-raw`, a space, the format version as a decimal number.
- Header lines: `key: value`. Keys are lowercase letters, digits and hyphens. Values are UTF-8
  with no line breaks. Look keys up by name; don't rely on their order.
- An empty line ends the header.
- Each section: the line `section NAME LENGTH`, then exactly LENGTH bytes of body, then CRLF.
  Names use letters, digits, `_`, `.`, `/` and `-`. No name appears twice.
- The line `end`, and nothing after it. A record without it is truncated.

## Header

| Key | Example | Meaning |
|---|---|---|
| `r2x-version` | `0.3.0` | r2x version that wrote the record |
| `response-exe-sha256` | `bbf4bc59…` | SHA-256 of `r2k.exe` |
| `wine-version` | `wine-9.0 (Ubuntu 9.0~repack-4build3)` | output of `wine --version` |
| `input-name` | `Newbeam.r2t` | input file name, or `File > New` when there is no input |
| `input-sha256` | `036440c7…` | SHA-256 of the input file's bytes; absent with no input |
| `template-sha256` | `0e74ef3d…` | with no input, SHA-256 of `r2k.r2k`, Response's template for new sections, if the program folder has one; absent otherwise |
| `units` | `si` | units in effect: `si`, `us` or `kgcm` |
| `factors` | `0.65,0.85,0.90` | material factors in effect: concrete, steel, prestress |
| `initial` | `-2000.00,0.00,0.00` | initial load in effect: N, M, V in the units in effect |
| `increment` | `0.00,1.00,1.00` | load increment in effect: N, M, V |
| `more-detail` | `2` | Solve > More Detail presses that refined the solve (`--more-detail`), `0` without; absent in records from r2x 0.1.0 and 0.2.0 |
| `views` | `general,cracking,reinforcement,no-shear` | detail views captured (`--views`), in this order; absent in records from r2x 0.1.0, which captured `no-shear` only |
| `stage-count` | `60` | load stages in the solve, numbered 0 to `stage-count` − 1; 0 is the initial load |
| `peak-stage` | `56` | the stage Response shows when the solve finishes |
| `detail-stages` | `0-5,56` | stages with detail-view sections, as numbers and ranges |

The four settings keys are read back from Response's Preferences and Define Loading dialogs
after r2x has applied its options, as the dialogs show them: two decimals, so a load of 0.738
kip-ft reads `0.74`. Records from r2x 0.1.0 and 0.2.0 always have V = 0 (shear was out of scope
until 0.3.0).

With More Detail, stage numbers, `stage-count`, `peak-stage` and `detail-stages` are those of
the refined solve: each press puts new stages between the old ones up to the peak, so the same
load stage has a higher number after it.

## Sections

Control charts, every stage, one point per stage:

| Name | Response chart (`Title :` line of the export) |
|---|---|
| `control/moment_ex` | `Control : Moment - \|e_x` |
| `control/moment_phi` | `Control : Moment - \|f` |
| `control/axial_ex` | `Control : Axial Load - \|e_x` |
| `control/shear_gxy` | `Control : Shear - \|g_x_y` |
| `control/shear_ex` | `Control : Shear - \|e_x` |

Which two there are depends on the increment, and they are in the record in screen order (top
first):

| Increment | Sections |
|---|---|
| no shear, with a moment (or 0,0,0) | `moment_ex`, `moment_phi` |
| axial load alone | `axial_ex` alone: Response shows the same chart in both places |
| shear and a moment | `shear_gxy`, `moment_phi` |
| shear and an axial load | `shear_gxy`, `axial_ex` |
| shear alone | `shear_gxy`, `shear_ex` |

Shear–γxy's γxy is the average shear strain weighted by shear force over the section
(∫ τ γxy b dy / V), not the strain at any one depth (docs/cli.md, *Shear and More Detail*).
An increment of 0,0,0 gives two stages, 0 and 1, both at the initial load.

Detail views, for each stage N in `detail-stages` (N without leading zeros):

| Name | Response chart (`Title :` line of the export) | Views |
|---|---|---|
| `stage/N/longitudinal_strain` | `Longitudinal Strain` | General, Cracking, Reinforcement, No Shear |
| `stage/N/transverse_strain` | `Transverse Strain` | General, Reinforcement |
| `stage/N/shear_strain` | `Shear Strain` | General |
| `stage/N/shear_stress` | `Shear Stress` | General |
| `stage/N/principal_compressive_stress` | `Principal Compressive Stress` | General |
| `stage/N/shear_on_crack` | `Shear on Crack` | General |
| `stage/N/principal_tensile_stress` | `Principal Tensile Stress` | General |
| `stage/N/principal_tensile_strain` | `Principal Tensile Strain` | Cracking |
| `stage/N/crack_widths` | `Crack Widths` | Cracking |
| `stage/N/average_angle` | `Average Angle` | Cracking |
| `stage/N/long_crack_spacing` | `Long. Crack Spacing` | Cracking |
| `stage/N/transverse_crack_spacing` | `Transverse Crack Spacing` | Cracking |
| `stage/N/diagonal_spacing` | `Diagonal Spacing` | Cracking |
| `stage/N/long_reinforcement_stress` | `Long. Reinforcement Stress` | Reinforcement, No Shear |
| `stage/N/long_reinf_stress_at_crack` | `Long. Reinf Stress at Crack` | Reinforcement, No Shear |
| `stage/N/long_average_bond` | `Long. Average Bond` | Reinforcement |
| `stage/N/stirrup_stress` | `Stirrup Stress` | Reinforcement |
| `stage/N/stirrup_stress_at_crack` | `Stirrup Stress at Crack` | Reinforcement |
| `stage/N/transverse_average_bond` | `Transverse Average Bond` | Reinforcement |
| `stage/N/shrinkage_thermal_strain` | `Shrinkage & Thermal Strain` | No Shear |
| `stage/N/longitudinal_concrete_stress` | `Longitudinal Concrete Stress` | No Shear |

These are the charts with a data export in the four views r2x captures, as Response names them
in its view list. A stage has the charts of the views in the `views` key, each chart once: one
that recurs in several views (Longitudinal Strain is in all four) is the same export in each, and
r2x checks that. The other cells of each nine-chart view (cross section, crack diagram, internal
forces, N+M) are pictures only. Where each chart sits in its view is in `src/r2x/views.json`.

Order: the control charts as Response places them (top first), then each stage in
`detail-stages` ascending, with its charts in the order of the table above, leaving out views not
captured. With `--views no-shear` a record has the same sections, in the same order, as one from
r2x 0.1.0.

Each body is exactly what Response put on the clipboard (CF_TEXT) for Copy Chart Data: ASCII
with CRLF line endings, Greek letters spelled as Response spells them (`|e_x` for εx, `|f` for φ).
r2x checks each export's `Title :` line, and matches each stage's strain profile to the control
curves (εx where there is an εx curve, curvature where there is a Moment–φ curve), before it
writes anything.

## Guarantees

- **Byte for byte.** Bodies are never re-encoded, trimmed or reformatted.
- **Deterministic.** The same input, settings and versions give the same bytes: there are no
  timestamps or timings in the record (progress on stderr has those).
- **Whole or nothing.** The worker writes the record under a temporary name and renames it once
  complete. A failed solve leaves no record.

## Versioning

The first line carries the format version, now `1`.

- Adding a header key or a new kind of section keeps the version. Readers ignore keys and
  sections they don't know.
- Changing the framing, or the meaning of an existing key or section, raises it.
- A reader refuses a record whose version is newer than it knows.
