# Risk register: where r2x's results could differ from Response on Windows

Item 5 of *Before setting r2x down* starts here, not from runs. Each risk is something that
could make r2x's record or report differ from what an engineer would get by running Response by
hand on Windows. For each: whether the engineer can see it, what covers it today, and the
cheapest check that would catch it.

**Seeing it** decides the kind of check. An error the engineer can see (the section is not the
one asked for, a load is wrong) is caught the way it is in the GUI: by looking at the input
before trusting the output, so the report must show it. An error the engineer cannot see (a
wrong stage, a solve read early, a digit off under Wine) needs a mechanical check against an
independent oracle, and only hand captures on Windows are independent of r2x.

Tiers, cheapest last: **A**, hand captures on Windows (the only independent oracle; Jamie's
time); **B**, r2x's worker run natively on Windows against Wine (not in the first pass);
**C**, checks on records alone, at scale, no oracle.

## Solving

| # | Risk | Seen? | Covered today | First pass |
|---|---|---|---|---|
| S1 | A setting applied wrong: units, factors, initial or increment | Yes: the solve report shows Preferences and Define Loading as set; the header reads them back from the same dialogs | Tier A: US units, CSA factors, constant N, N increment, V increment | Nothing new. kg/cm units and two settings combined stay on the gap list, low |
| S2 | An input opened differently: `.rsp` files, File Override, units stored in the file | Partly: the input screen | Cm4.rsp and Response's shear examples run, no reference | **Tier A**: Marshall.rsp |
| S3 | The wrong stage picked where several look alike (common near a shear peak) | No: the record names the stage, nothing shows it was the right one | r2x's paging check (exports compared stage by stage); no Windows reference for a case that needs the fallback | **Tier A**: Marshall.rsp (its peak matches 5 stages) |
| S4 | A solve read before it finished (Wine gives no signal) | No: a short solve looks like a real one | Finish rule: bottom curve unchanged 1 s and Response idle; every Tier A case | **Tier C**: solve each case twice, same bytes |
| S5 | Wine numerics: signed zeros, last-digit rounding | No | Tier A byte comparisons in nine cases; one known signed zero | Accepted for now; breadth is Tier B's, in the clone project |
| S6 | A chart read from the wrong cell or menu item | No, but loud: every export's title is checked | Title check, `views.json`, the menu-width check | Nothing new |
| S7 | Stages away from the peak paged to wrongly | No | Identification at every stage; Tier A at Newbeam 36 and newbeam-shear 20 | **Tier A**: Cm4.rsp at a stage well below its peak; **Tier C**: stages in order, control curve monotonic in the loading parameter |
| S8 | Shear with an axial load: N and V together | No | r2x's own checks under Wine | **Tier A**: Newbeam, constant N with an M and V increment |
| S9 | An increment with N, M and V all non-zero | No | None | **Tier A**: Newbeam, increment with all three |
| S10 | More Detail: presses miscounted, the limit misread | Partly: the header's `more-detail` | newbeam-moredetail (twice); `max` under Wine | Nothing new |
| S11 | Results that are Response's but wrong for the section: equilibrium, closed forms | Only by engineering judgment | None: r2x returns Response's bytes and checks none of them | **Tier C**: equilibrium of the exported stresses against N and M; squash load; cracking moment |

## Defining a section

| # | Risk | Seen? | Covered today | First pass |
|---|---|---|---|---|
| D1 | A field set in the wrong control, or not set | Mostly: the input screen shows most fields (see *What the report leaves out*) | Wine: every dialog lands where Response saves it; Windows: five cases | Short Tier A cases aimed at what the screen does not show |
| D2 | Response reacting differently as values go in (fields enabled by shape, bars checked, Modify's precision) | Sometimes: Response's messages come through | The five Windows cases; Modify's precision known (63.90 becomes 64.00) | The other eight define cases cut to two or three short ones |
| D3 | A new section's layers in another order | No, and harmless: same section, same record | Matched by solving (`compare.py`) | Nothing new |

## The program folder (new with linking)

| # | Risk | Seen? | Covered today | First pass |
|---|---|---|---|---|
| L1 | Another build of `r2k.exe` | Yes: refused unless `--allow-unverified`, and then marked in the header | SHA-256 check at setup and every run | Built with linking (item 2) |
| L2 | The user's own `rebar.dat` or `shape.dat` (bar and shape lists) | Only through the header's files hash | None | A files hash in the header; `r2x health` names the files that differ from the verified folder |
| L3 | `Response.ini` and the user's own sections in the folder | No | Not copied into the job (only the files Response reads) | Built with linking |

## The image

| # | Risk | Seen? | Covered today | First pass |
|---|---|---|---|---|
| E1 | A rebuild drifts (the base is `ubuntu:24.04` by tag; only Wine is pinned) | No | Rerun the Wine tests after any rebuild | The verified image published (GHCR), so users run the bytes that were checked |

## What the report leaves out

For deciding whether inspection is enough for v1.0 (D1, and Jamie's idea under item 2).
Response's input screen, checked on 2026-11-07 with Newbeam and with Newbeam plus a tendon
layer, crack spacing set and the moment axis moved, shows: section properties; each layer's
bars (`3 - 25M`) and a tendon's prestrain (`Δεp = 6.50 mm/m`); stirrups and spacing; clear
cover; crack spacing (the formula, or `sx = 300.0`); a moment axis away from the centroid
(`Axial load applied 250 mm from bottom`); the loads, constant and increment; units; and the
materials' key values (f'c, ft, fu, fy of each type, fpu). Earlier notes had the prestrain as
not shown; it is.

It does not show:

- Bar and tendon depths as numbers (the layers are drawn to scale; the cover is given).
- A tendon's slope.
- The material factors, in a define's report (the solve report shows them in Preferences).
- Title comments and Analysis By (only the title).
- Stages other than the peak, and how the stage was identified (the record says which stage,
  not why).

## First pass

Status on 2026-11-07:

- **Tier A, four captures, ready to make** on Windows, each aimed at what the engineer cannot
  see: `tests/reference/marshall` (S2, S3: an `.rsp` whose peak needs the paging fallback),
  `cm4` (S2, S7: an `.rsp`, at its peak and 38 stages below), `newbeam-axial-shear` (S8) and
  `newbeam-nmv` (S9). Each README has the recipe and what r2x gives under Wine, to confirm the
  stage on Windows. `tests/test_worker_wine.py` solves each now and compares it byte for byte
  once its exports are in the folder.
- **Define:** the eight cases not yet made cut to three short ones (`general`, `section`,
  `tendons-add`), aimed at how r2x works Response's dialogs where Response reacts as values go
  in (D1, D2). `tests/reference/define/README.md` says why the other five went.
- **Tier C prototype**, `tools/tier_c.py` (plain reinforced sections, SI):
  - *Equilibrium* (S11): the exported concrete and bar stresses against the stage's N and M.
    Under Wine, Newbeam at every stage under a moment, an axial load alone, a constant N, M
    and V together, and at the peak with N and V, N, M and V, and Marshall.rsp: 187 stages,
    every residual within 0.5 % of the internal forces. On the Windows exports in
    `tests/reference` too (`tests/test_tier_c.py`). Response's concrete is net of the bars:
    counting it gross leaves the top bar's share (about 10 kN in Newbeam) unbalanced. It
    catches garbage and a wrong stage far from the right one, not a neighbour near the peak,
    where stages differ by fractions of a kNm.
  - *Stage order* (S7): the bottom chart's deformation moves one way up to the peak. εx at the
    centroid reverses early as a section cracks, and shear failures unload after their peak,
    so only the bottom chart, and only up to the peak, is checked.
  - *Squash load* (S11), for judgment: Newbeam's axial-only peak is 0.912 of f'c (Ag − As) +
    fy As. The closed form assumes a uniform strain, and Response's exports at the peak show
    none: concrete from −35.0 to −27.8 MPa, the top 20M at −400 MPa and the bottom 3–25M at
    −253.6 MPa. (A first reading on 2026-11-07, that the concrete carried 0.90 f'c with the
    bars at fy, assumed the uniform strain and was wrong.) The tool now prints the stresses at
    the peak beside the ratio.
  - *Repeat* (S4): Newbeam solved twice gives the same sections, at the peak in the container
    against the host, and at every stage on the host.
- **Not now:** Tier B; kg/cm units and two settings combined (S1 is visible); a cracking-moment
  check; sections with tendons and other units in Tier C.
