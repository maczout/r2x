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
rec.stage(56, "longitudinal_strain")             # bytes of one detail-view export
rec.stages()                                     # [56]
```

Don't open a record in an editor and save it: an editor that changes line endings or encoding
breaks the lengths, and `record.read` then refuses the file.

## Layout

```
r2x-raw 1                                    format name and version
r2x-version: 0.1.0                           header: one "key: value" per line
response-exe-sha256: bbf4bc59…
…
units: si
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
| `r2x-version` | `0.1.0` | r2x version that wrote the record |
| `response-exe-sha256` | `bbf4bc59…` | SHA-256 of `r2k.exe` |
| `wine-version` | `wine-9.0 (Ubuntu 9.0~repack-4build3)` | output of `wine --version` |
| `input-name` | `Newbeam.r2t` | input file name, or `File > New` when there is no input |
| `input-sha256` | `036440c7…` | SHA-256 of the input file's bytes; absent with no input |
| `template-sha256` | `0e74ef3d…` | with no input, SHA-256 of `r2k.r2k`, Response's template for new sections, if the program folder has one; absent otherwise |
| `units` | `si` | units in effect: `si`, `us` or `kgcm` |
| `factors` | `0.65,0.85,0.90` | material factors in effect: concrete, steel, prestress |
| `initial` | `-2000.00,0.00,0.00` | initial load in effect: N, M, V in the units in effect |
| `increment` | `0.00,1.00,0.00` | load increment in effect: N, M, V |
| `stage-count` | `60` | load stages in the solve, numbered 0 to `stage-count` − 1; 0 is the initial load |
| `peak-stage` | `56` | the stage Response shows when the solve finishes |
| `detail-stages` | `0-5,56` | stages with detail-view sections, as numbers and ranges |

The four settings keys are read back from Response's Preferences and Define Loading dialogs
after r2x has applied its options, as the dialogs show them: two decimals, so a load of 0.738
kip-ft reads `0.74`. V is always 0, since an input with shear is out of scope.

## Sections

| Name | Response chart (`Title :` line of the export) | Stages |
|---|---|---|
| `control/moment_ex` | `Control : Moment - \|e_x` | every stage, one point each |
| `control/moment_phi` | `Control : Moment - \|f` | every stage, one point each |
| `control/axial_ex` | `Control : Axial Load - \|e_x` | every stage, one point each |
| `stage/N/longitudinal_strain` | `Longitudinal Strain` | stage N |
| `stage/N/shrinkage_thermal_strain` | `Shrinkage & Thermal Strain` | stage N |
| `stage/N/long_reinforcement_stress` | `Long. Reinforcement Stress` | stage N |
| `stage/N/long_reinf_stress_at_crack` | `Long. Reinf Stress at Crack` | stage N |
| `stage/N/longitudinal_concrete_stress` | `Longitudinal Concrete Stress` | stage N |

Which control charts there are depends on the loading: `moment_ex` and `moment_phi` when the
increment includes a moment; `axial_ex` alone for an axial-only increment, where Response shows
the same chart in both control positions. The detail views are the five No Shear charts that
have a data export. N is the stage number without leading zeros. Order: the control charts as
Response places them (top first), then each stage in `detail-stages` ascending, with its charts
in the order of the table.

Each body is exactly what Response put on the clipboard (CF_TEXT) for Copy Chart Data: ASCII
with CRLF line endings, Greek letters spelled as Response spells them (`|e_x` for εx, `|f` for φ).
r2x checks each export's `Title :` line, and matches each stage's strain profile to the control
curves (εx, and curvature where there is a Moment–φ curve), before it writes anything.

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
