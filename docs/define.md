# r2x define and the r2x session

**Status:** built under Wine on 2026-10-27/28 from the plan (the Claude Doc "r2x define and the
r2x session — plan", phases D0, D1 and D2), on the branch `define`. Not yet checked on
Windows: that is the reference cases in `tests/reference/define` (below), and the report's
reload in a Windows browser. r2x 0.4.0 is released once they match.

`r2x define` sets one of Response-2000's dialogs for a section, question by question, and lets
Response save the file; `r2x` with no command is a session at an `r2x>` prompt, where a section
goes from nothing to a solved record without opening Response. Response does all the work,
through its own dialogs and its own Save As: r2x never reads or writes the section's XML, and
works nothing out. `README.md` has the usage; this file has how it works and what was found.

## How a define step works

One container run per step, as for a solve (the file chain of the plan):

1. Response starts from a fresh copy of its program folder and opens the section's file (for
   `define quick` with no file to replace, it starts empty).
2. The dialog is opened with its menu command, and its fields are gone through in the
   dialog's order (`src/r2x/dialogs.json`). For each, the worker reads what the dialog shows
   (its value, its label and unit, which can change: Select bar by area turns Bar Designation
   into Bar Area, mm^2) and asks the question; the command line prompts, checks only that a
   number is a number (and a choice one of the choices), and sends the answer back. A field is
   set only when the answer differs from what the dialog shows, so **Enter leaves a field
   exactly as Response had it**. Disabled fields are skipped (the dimensions a shape does not
   have); so is a value behind a ticked Automatic check box.
3. Response's own dialogs along the way are passed on in its words (below).
4. OK (or Finish); for a new section, Edit General's date is set to today's date on the
   Windows side, since Response dates it by the container's clock, which is UTC. If nothing was
   changed, Cancel instead, and nothing is saved.
5. File > Save As, through Wine's common dialog (command 24334, the file name in control
   1148), to a folder of the job's own; the bytes are then written over the section's file,
   under a temporary name first.
6. The dialog is opened again and read back: the prompt prints what changed, as the dialog
   now shows it (for Quick Define, as its pages showed it before Next).
7. The section's report, `NAME.r2x.html` beside the file, is rewritten: Response's input screen
   after Save As, and the dialog as r2x left it (a wizard's four pages).

The worker and the command line talk over the container's stdin and stdout (`docker run -i`),
one JSON object per line (`src/r2x/ask.py`): `ask` (a question; the answer comes back on
stdin), `say`, `set` (the read-back), `show`, `done`. End of input means the person gave up: the
worker stops without saving. Progress and errors stay on stderr in `r2x.progress`'s form.

**Why a file per step:** a section defined in memory exports slightly differently from the
same section read back from its file (found with File > New in 0.1.0): Response sorts the
longitudinal layers by depth when it opens a file, and keeps a section defined in memory in the
order they were added. A file opened and saved again keeps its bytes from then on. So after its
first step a section is always the file Response wrote, and anyone who opens it gets the same.

**Units first.** Quick Define's defaults follow the units in effect: in US units they are a
10 × 24 in beam with #6 and #8 bars, f'c 5000 psi. So `define quick` on an existing file opens
that file first (its units, through File Override), and in a session with no file yet,
`define units` is remembered for the `define quick` that follows. Switching units with
`define units` converts the section in memory as Preferences does, and the file is saved in
those units, with Response's rounding (found in 0.1.0).

## Response's own dialogs

| What Response shows | When | What r2x does |
|---|---|---|
| "Do you wish to create a new section?" (Yes/No) | Quick Define on an existing section | answers Yes: `define quick` always starts a new section |
| any other Yes/No message box | e.g. setting fy while Materials shows "Detailed" ("Changing this value will overwrite the detailed parameters"); Add with a name that exists; Modify with a new name | asks it, word for word, with no default answer |
| a message box with OK | a message | shows it, presses OK |
| **Reinforcement Types** (a list) | leaving a Quick Define page, or Add/Modify, with a bar designation Response does not know | asks for a bar from Response's list: its rows are the lines of `rebar.dat` in order, so the answer picks the row with that name. No default: Response's own Cancel quietly takes the first row (10M) |
| **View Data** ("Errors in defining Section ...") | after Finish, for errors Response has already fixed ("Negative width found ... Made positive") | shows the text; the section is as Response made it (the report's input screen shows it; undo in a session) |

Response checks little. Quick Define takes a negative f'c or width and makes it positive
(f'c −5 is saved as 5.0), and takes "abc" for f'c; r2x refuses anything that is not a number
before it reaches the dialog. Bars are the exception: an unknown designation brings up the list.

## The dialogs

The survey by `python tools/define_survey.py` (Newbeam: Quick Define's defaults, then
`tests/reference/newbeam/input.r2t` for the others). **Control**: the control ID (RT_DIALOG of
r2k.exe, `docs/r2k-dialogs.txt`); **Precision**: decimals the dialog shows; **Saved as**: the
element and attribute of the saved file. "(not shown)": a field Newbeam's dialog does not show
(a shape's unused dimensions, disabled; a spacing or axis behind its ticked Automatic box,
which shows "Automatic" or "Centroid" and 0.0 once unticked).

| Noun | Field | Question | Control | Kind | Newbeam shows | Precision | Saved as |
|---|---|---|---|---|---|---|---|
| quick | title | Title | 5060 | text | New Cross Section | text | r3g_beam name |
| quick | analysis-by | Analysis By | 5061 | text | (blank) | text | r3g_beam doneby |
| quick | fc | Concrete Cylinder Strength | 5064 | number | 35.0 MPa | 1 dp | concrete fcp |
| quick | fy | Long. Steel Yield Strength | 5031 | number | 400 MPa | 0 dp | rebar fy |
| quick | fyt | Transverse Steel Yield | 5065 | number | 400 MPa | 0 dp | rebar name=Trans fy |
| quick | prestress | Prestressed Steel Type | 5070 | choice | 1860 MPa Low Relaxation 13 mm strands | text | prestress |
| quick | shape | Shape | 5025 | shape | Rectangle | text | shapesection name |
| quick | dim1 | Dimension 1 | 5060 | number | 250 mm | 0 dp | shapesection par1 |
| quick | dim2 | Dimension 2 | 5061 | number | 600 mm | 0 dp | shapesection par2 |
| quick | dim3 | Dimension 3 | 5062 | number | (not shown) |  | shapesection par3 |
| quick | dim4 | Dimension 4 | 5123 | number | (not shown) |  | shapesection par4 |
| quick | dim5 | Dimension 5 | 5064 | number | (not shown) |  | shapesection par5 |
| quick | dim6 | Dimension 6 | 101 | number | (not shown) |  | shapesection par6 |
| quick | top-number | Top, Number of Bars | 5060 | integer | 1 | 0 dp | longreinfx name=top num |
| quick | top-by-area | Top, Select bar by area | 107 | check | n | text | - |
| quick | top-bar | Top, Bar Designation | 5061 | bar | 20M | text | longreinfx name=top bartitle |
| quick | bottom-number | Bottom, Number of Bars | 5062 | integer | 3 | 0 dp | longreinfx num |
| quick | bottom-by-area | Bottom, Select bar by area | 5014 | check | n | text | - |
| quick | bottom-bar | Bottom, Bar Designation | 5123 | bar | 25M | text | longreinfx bartitle |
| quick | stirrup-type | Stirrup Type | 5004 | choice | T Headed single leg | text | transreinfz pattern |
| quick | stirrup-by-area | Stirrups, Select bar by area | 5067 | check | n | text | - |
| quick | stirrup-bar | Stirrups, Bar Designation | 5061 | bar | 10M | text | transreinfz bartitle |
| quick | spacing | Spacing | 5062 | number | 250 mm | 0 dp | transreinfz space |
| quick | cover | Clear Cover | 5065 | number | 40 mm | 0 dp | transreinfz disttop, distbot |
| quick | strands | Number of strands | 5041 | integer | 0 | 0 dp | longreinfx num (a tendon layer) |
| quick | prestrain | Delta-Epsilon P | 5044 | number | 6.500 mm/m | 3 dp | longreinfx dep |
| general | title | Title | 5032 | first-line | New Cross Section | text | r3g_beam name |
| general | comments | Comments | 5032 | other-lines | (blank) | text | r3g_beam name (after the first line) |
| general | analysis-by | Analysis By | 5870 | text | (blank) | text | r3g_beam doneby |
| general | date | Date | 5050 | text | 2026/10/24 | text | r3g_beam date |
| general | auto-long-spacing | Automatic Longitudinal Spacing | 101 | check | y | text | - |
| general | long-spacing | Longitudinal Spacing | 5042 | number | (not shown) |  | r3g_beam smx |
| general | auto-trans-spacing | Automatic Transverse Spacing | 103 | check | y | text | - |
| general | trans-spacing | Transverse Spacing | 5043 | number | (not shown) |  | r3g_beam smt |
| general | centroidal-axis | Centroidal Moment axis | 5871 | check | y | text | - |
| general | moment-axis | Moment axis | 5044 | number | (not shown) |  | r3g_beam axialloc |
| materials | fc | Concrete Cylinder Strength | 104 | number | 35.0 MPa | 1 dp | concrete fcp |
| materials | fy | Reinforcement Yield Strength | 105 | number | Detailed MPa | text | rebar fy (every type) |
| materials | fpu | Prestressed Reinforcement Strength | 322 | number | 1860 MPa | 0 dp | prestress fu |
| section | shape | Shape | 5025 | shape | Rectangle | text | shapesection name, sectionSOLID |
| section | dim1 | Dimension 1 | 5060 | number | 250 mm | 0 dp | shapesection par1 |
| section | dim2 | Dimension 2 | 5061 | number | 600 mm | 0 dp | shapesection par2 |
| section | dim3 | Dimension 3 | 5062 | number | (not shown) |  | shapesection par3 |
| section | dim4 | Dimension 4 | 5123 | number | (not shown) |  | shapesection par4 |
| section | dim5 | Dimension 5 | 5064 | number | (not shown) |  | shapesection par5 |
| section | dim6 | Dimension 6 | 101 | number | (not shown) |  | shapesection par6 |
| long | number | Number of Bars | 5060 | integer | bot: 3; top: 1 | 0 dp | longreinfx num |
| long | by-area | Select bar by area | 5084 | check | bot: n; top: n | text | - |
| long | bar | Bar Designation | 5062 | bar | bot: 25M; top: 20M | text | longreinfx bartitle, A |
| long | depth | Dist. from Bottom | 5063 | number | bot: 64 mm; top: 539 mm | 0 dp | longreinfx z |
| long | type | Rebar Type | 5070 | choice | bot: Steel 1; top: Steel 1 | text | longreinfx type |
| trans | spacing | Stirrup Spacing | 5060 | number | stirrup: 250 mm | 0 dp | transreinfz space |
| trans | by-area | Select bar by area | 5084 | check | stirrup: n | text | - |
| trans | bar | Bar Designation | 5062 | bar | stirrup: 10M | text | transreinfz bartitle, A |
| trans | top | Dist. to Top | 5063 | number | stirrup: 554 mm | 0 dp | transreinfz disttop |
| trans | bottom | Dist. to Bottom | 5064 | number | stirrup: 46 mm | 0 dp | transreinfz distbot |
| trans | bar-type | Bar Type | 322 | choice | stirrup: T Headed single leg | text | transreinfz pattern |
| trans | type | Rebar Type | 5070 | choice | stirrup: Trans | text | transreinfz type |
| tendons | number | Number of Strands | 5060 | integer | no tendon layers |  | longreinfx num |
| tendons | by-area | Select bar by area | 5084 | check | no tendon layers |  | - |
| tendons | strand | Strand Designation | 5062 | bar | no tendon layers |  | longreinfx bartitle, A |
| tendons | prestrain | Prestrain | 5063 | number | no tendon layers |  | longreinfx dep |
| tendons | depth | Dist. from Bottom | 5064 | number | no tendon layers |  | longreinfx z |
| tendons | slope | Slope of Tendon | 5065 | number | no tendon layers |  | longreinfx slope |
| tendons | type | Tendon Type | 5070 | choice | no tendon layers |  | longreinfx type |
| loads | axial | Axial Load, Constant | 101 | number | 0.00 kN | 2 dp | sectloading BN |
| loads | moment | Moment, Constant | 5052 | number | 0.00 kNm | 2 dp | sectloading BM |
| loads | shear | Shear, Constant | 5053 | number | 0.00 kN | 2 dp | sectloading BV |
| loads | axial-increment | Axial Load, Increment | 5054 | number | 0.00 kN | 2 dp | sectloading MN |
| loads | moment-increment | Moment, Increment | 5055 | number | 1.00 kNm | 2 dp | sectloading MM |
| loads | shear-increment | Shear, Increment | 5056 | number | 0.00 kN | 2 dp | sectloading MV |
| units | units | Units | 5028/5029/5030 | radio | SI Metric | text | r3g_beam units |
| factors | concrete | Material Factors, Concrete | 5041 | number | 1.00 | 2 dp | analysisoptions phic |
| factors | steel | Material Factors, Steel | 5044 | number | 1.00 | 2 dp | analysisoptions phis |
| factors | prestress | Material Factors, Prestress | 5045 | number | 1.00 | 2 dp | analysisoptions phip |

Templates: Quick Define's pages are dialogs 300, 302, 303 and 304; Edit General 120; the
Materials Page's Basic Properties 14; the Concrete Section's Basic Shapes 310; the
Longitudinal, Transverse and Tendon pages all use dialog 13 (Details: a list box 5072, Name
5081, Add/Modify/Delete 5075–5077); Define Loading 5; Preferences 320.
`tests/test_define.py` checks every control ID in the catalogue against these templates.

Menu commands (RT_MENU of r2k.exe 1.9.7): Quick Define 150, Edit General 103, Material
Properties 117 (a sheet, "Materials Page"), Concrete Section 153 (a sheet: Basic Shapes,
Standard Shapes, User Defined), Longitudinal Reinforcement 156 (a sheet: Individual Layers,
Circular Patterns, Distributed Patterns, Define Tendon Layers), Transverse Reinforcement 154
(one page, Define Stirrups), Tendons 5098 (one page, Define Tendon Layers), Sectional Loads 152,
Preferences 321, Save As 24334.

## Findings

Found under Wine on 2026-10-27 and 28, on Newbeam and on sections made with Quick Define.

- **Quick Define with every default gives Newbeam**: saved straight away, the file is
  `tests/reference/newbeam/input.r2t` byte for byte once the date is Newbeam's (the first
  test in `tests/test_define_wine.py`). It needs no File > New (24331, which does not answer
  a posted message under Wine): Define > Quick Define opens the same wizard.
- **Quick Define's derived values:** Response works out the bar layers (six 30M bars in a
  300 mm web become two layers, `bot3` and an unnamed one), `fu` (1.5 fy), the member length
  and the moment diagram. Those are Response's; r2x only answers its questions.
- **A file opened and saved sorts its layers**; opened and saved again it keeps its bytes.
  Adding a layer and deleting it again leaves the file byte for byte as it was before.
- **The order of a new section's layers is not reliable** (found with the Windows references,
  2026-10-28). Quick Define's T-beam and I-girder made by hand on Windows and by r2x hold the
  same layers with the same values, but the layer Quick Define splits off (`bot3`, the fourth
  strand layer) comes last in the hand-made file and first in r2x's. Opened and saved again by
  Response, the two are the same bytes, and they solve to the same record. Whether typing
  through the wizard or Windows against Wine makes the difference is not known; nothing after
  Response's first opening of the file sees it. So a reference case matches when its files are
  the same bytes, or else the same section with the layers in another order that solves to the
  same record (`tests/reference/define/compare.py`).
- **Modify takes every field as the dialog shows it**, as in the GUI: Newbeam's bottom layer
  at 63.90 shows as 64 (Dist. from Bottom has no decimals), so a modify that changes only its
  bar count stores z = 64.00. Quick Define's derived depths survive only until a layer is
  modified. Add uses the fields shown too; its defaults are the selected layer's.
- **Names:** Response lists the unnamed bottom layer as `bot` (and saves no `name` for it).
  Add with a name that exists asks whether to modify the existing layer, and then, since the
  layer selected is another, whether to overwrite it; answered No, Response adds the layer as
  `top1`, and r2x follows the name Response gave. Modify with a new name asks whether to
  overwrite the existing type; answered No, Response adds a new type beside the old one.
- **Materials:** with more than one rebar type of the same strength (Newbeam: Steel 1 and
  Trans), Basic Properties shows fy as "Detailed". Setting it asks to overwrite the detailed
  parameters; Yes merges every type into one, Steel 1 (Trans goes, and the stirrups use
  Steel 1). Enter leaves it alone.
- **Concrete Section** changes the shape only: the bars stay where they were.
- **Loads** are saved in `<sectloading>` as `BN`, `BM`, `BV` (constant) and `MN`, `MM`, `MV`
  (increment), each only when it differs from Response's default, as found in 0.3.0.
- **Title and comments** share Edit General's one box: the first line is the title, the
  others the comments, saved together in `name` (and in the member's material type). The main
  window's title then has a line break, which the helper now turns into a space.
- **Tendons** are `longreinfx` layers with a prestrain (`dep`); Define Tendons lists only
  those. Strand designations come from `rebar.dat` as bars do (S13, ...).
- **Quick Define and prestressing None:** the strands field stays enabled, labelled
  "Number of 13 mm strands".
- **A circular section** in Quick Define has 16 top bars and no bottom bars by default, and
  hoops.

## The helper

New commands in `src/r2x/worker/helper.c`: `ctls` (a dialog's controls with their IDs and
enabled state), `enabled`, `lbitems`, `lbget`, `lbselect` (a list box, with its change
notification), `psget`, `psselect` (a property sheet's page), `lvitems`, `lvget`,
`lvselect` (a list view, the shape pickers) and `sclick` (a click that is sent, so its reply
comes once Response has handled it). A list view's messages carry pointers, which must point
into Response's own process: the helper puts the structure and the text buffer there with
`VirtualAllocEx` and copies them back with `ReadProcessMemory`, which Wine supports.

`settext`, `sclick` and the select commands send with a short timeout (0.8 s) and reply
`ok busy` if Response is still handling the message: in practice Response is showing a dialog
of its own (the message completes when it closes), which the worker then passes on. Before,
setting fy in Materials blocked the helper for its full 5 s timeout behind Response's question.

## The report reloads itself

A define step rewrites the section's report, the same `NAME.r2x.html` that `solve --report`
writes, with the inputs only: Response's input screen after Save As, and the dialog just set.
A define after a solve so takes the outputs out, and the report never shows results for an
input that has changed since; a solve in a session writes it whole again.

Every report reloads itself when r2x rewrites it, with no server and no files besides it. A
page opened from disk (`file://`) cannot read files, but it can frame one and be posted to by
it: every 1.5 s it loads itself, hidden, in a frame; that copy posts its stamp (a hash of the
page, at the top) to the page and stops loading there (`window.stop()`). A different stamp
means the file has changed: the page reloads, which keeps the place on it. Checked in
Chromium from `file://` (scroll position kept); to be checked in a Windows browser (Edge,
Chrome, Firefox). The pictures are inside the page, as before.

## Time per step

Under Wine in the cloud environment, the worker's time (Response starting, the dialog, Save
As, the pictures; the container adds about a second on the Framework):

| Step | Seconds |
|---|---|
| `define quick`, Enter throughout (four pages, four pictures) | 4.2 to 6.5 |
| `define quick` with answers on every page | 5.4 to 7.2 |
| `define general`, `section`, `loads`, `units`, `factors` | 2.7 to 3.3 |
| `define long add`, `delete`; `tendons add` | 3.2 to 3.9 |
| a step with one of Response's questions (`materials` fy, `trans` rename) | 4.1 to 5.2 |
| `show NOUN` | 1.8 to 2.3 |

## Decisions taken in building it

For Jamie to confirm or change (the plan's settled points are kept as they were):

- **The file name is asked by every `define quick` in a session**, defaulting to the
  session's file (or `new-cross-section.r2t`, from Response's title for a new section); the
  plan has it asked by the first define only. A file that exists, other than the session's,
  is replaced only after a yes; on the command line, `r2x define quick FILE` asks the same
  when FILE exists.
- **`define units` with no section yet** is remembered for the next `define quick` (units
  only: factors do not change Quick Define's defaults). Other defines need a section.
- **`show` changes nothing**, the report included; `show` alone is the file, its report, and
  whether its record is a solve of it as it is (by the record's input SHA-256).
- **`save FILE`** is Response's Save As (one container run) and the session goes on with
  FILE; `save` alone says the file is saved after every step.
- **`undo`** puts back the file from before the last step and rewrites the report with its
  input screen; a step that made a new file has nothing to put back (the file stays, and the
  session goes back to its file before).
- **The report opens in the browser** the first time a session writes it (only at a
  terminal); `report` opens it again.
- **Answers can be piped**, one per line (Enter: an empty line); at the end of the input
  every question is answered with Enter, and a question that needs an answer stops the step.
  The tests and `tests/reference/define/check.ps1` use this; it is not meant as an
  automation interface (that is a script that writes the input file).
- **Response's View Data errors after Finish** are shown, not asked again: the wizard has
  closed, and the section is as Response made it.

## Not done (later, each planned on its own, as in the plan)

Materials' Detailed pages and Rebar Details; circular and distributed bar patterns; standard
and user-defined shapes; shrinkage and thermal strains; a live container if steps feel slow; a
file with several sections (Response asks which to load: r2x stops with its question).

## Reference cases

`tests/reference/define`: thirteen cases, each made by hand in Response on Windows
(`hand.r2t`, steps in its `README.md`) and by r2x from the same answers (`session.txt`, an r2x
session). `check.ps1` runs them on Windows and compares; `tests/test_define_cases_wine.py`
does the same under Wine. `cases.json` holds the answers by field, and
`tools/define_cases.py` writes each case's `session.txt` and `README.md` from it. The three
Quick Define cases are compared but for the date.
