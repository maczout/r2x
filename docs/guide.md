# r2x user guide

For structural engineers using r2x. How it works inside, the tests and releasing are in
`docs/internals.md`; the record's exact layout is in `docs/raw-format.md`.

## What r2x is, and isn't

r2x runs **your own copy of Response-2000** (Bentz and Collins' sectional analysis program for
reinforced and prestressed concrete) without its window, from the command line. It does two
things:

- **Solve a section** and keep everything Response exports: both control charts at every load
  stage, and every chart with a data export in four detail views (General, Cracking,
  Reinforcement and No Shear), at the stages you ask for. The data is Response's own Copy Chart
  Data text, byte for byte, in one file per section: the **record**.
- **Define a section** question by question, through Response's own dialogs, with Response
  saving the file. A **report** beside the file shows Response's input screen after every step,
  so you can see the section as you build it.

Response does the work. r2x never edits your input file, never computes or adjusts a result,
and passes Response's own questions and messages on in its words. It runs Response under Wine
(a compatibility layer for running Windows programs on Linux) in a Linux container.

**Scope:** the sectional response (Solve > Sectional Response) to axial load, moment and shear,
optionally refined with Solve > More Detail. **Not:** M–N, M–V or N–V interaction, full member
response, the Load Deformation Plot or Mohr's Circles. Charts Response shows only as pictures
(the cross section, the crack diagram, internal forces) have no data, so they appear only in the
report.

**r2x does not check designs.** See *Disclaimer*, at the end.

## Installing

### Windows

1. **WSL 2 with Ubuntu 24.04**, and Docker Engine inside it (not Docker Desktop):

   ```bash
   sudo apt-get install docker.io docker-buildx
   sudo usermod -aG docker $USER        # then close and reopen the Ubuntu window
   ```

2. **Python 3.10 or later** in Windows, then r2x (standard library only, no other packages):

   ```powershell
   py -m pip install https://github.com/maczout/r2x/archive/refs/tags/v0.5.0.zip
   ```

3. **Response-2000**, from its author's site, [hadrianworks.com](https://www.hadrianworks.com/),
   installed or unzipped as usual. r2x needs its program folder: the one with `r2k.exe`.

4. **Link it, and get the image**, once:

   ```powershell
   r2x setup --response "C:\path\to\Response"
   ```

   This checks the folder (below), saves where it is, and pulls r2x's container image if it is
   not here yet (about 1.3 GB, once per version).

5. **Check:** `r2x health` shows the linked folder, whether its `r2k.exe` is the verified build,
   and the image's r2x and Wine versions.

The command line runs `wsl --exec docker ...` for you. Inputs and results must be on a drive
letter (`C:\...`), which WSL can see; network paths are not supported.

### Linux

Docker, Python 3.10+, the same `pip install`, and `r2x setup --response /path/to/Response`;
r2x calls `docker` directly.

### Updating

Install the new version with pip (add `--force-reinstall --no-cache-dir`, or pip may keep the
old one), then `r2x setup` pulls the image of the same version. Each version of r2x runs the
image with its own version number, so the two always match.

### Your copy of Response-2000

r2x links your program folder rather than shipping Response: nobody redistributes it, and you
run the copy you have.

- **The verified build.** r2x's results have been compared with Response on Windows for one
  build of `r2k.exe`: Response 1.9.7 (its splash screen says 1.9.6 beta), identified by its
  SHA-256 (`bbf4bc59…4e74`). `r2x setup` refuses another build, and so does every run, since
  the file could change. `r2x setup --response FOLDER --allow-unverified` links it anyway; every
  record then says `response-verified: no`, and nothing r2x has checked on Windows applies.
- **Which files.** Each run copies only the files Response reads (the program, its libraries,
  `rebar.dat`, `shape.dat`, `r3g.dtd`, and `r2k.r2k` if you have one) into a fresh folder of its
  own. Your `Response.ini` and any sections kept in the program folder are left out, and the
  folder is mounted read-only: r2x never writes to it.
- **Your bar and shape lists.** If you have edited `rebar.dat` or `shape.dat`, r2x uses yours,
  as Response would. `r2x health` names any file that differs from the verified folder, and the
  record's `response-files-sha256` changes with them.
- **Another folder for one run:** set `R2X_RESPONSE` to it. The setting is saved in
  `%APPDATA%\r2x\config.json` (`~/.config/r2x/config.json` on Linux).

## Solving

```
PS> r2x solve .\Newbeam.r2t --report
[Newbeam] solved: 60 stages, peak 56 -> Newbeam.r2x.txt, Newbeam.r2x.html (6.2 s)
```

Inputs are any files Response opens (`.r2t`, `.rsp`), several at once or a glob
(`.\cases\*.r2t`). With no input, r2x solves the section File > New gives (Newbeam, unless you
have an `r2k.r2k` template). Each input runs in its own container, about 5 to 10 s at the peak.

```
usage: r2x solve [INPUT ...] [options]

Run a full sectional response in Response-2000 1.9.7 and capture the data
from its control charts and detail views.

Scope: axial load, moment and shear. Not interaction diagrams or member
response.
r2x never edits the input file. Options override the input. Options you
leave out keep the input's value, or Response's start-up default if the
input has none.

Input:
  INPUT ...             .rsp or .r2t files; globs allowed (cases\*.r2t).
                        Default: a new section, Response's default (Newbeam).

Analysis:
  --units {si,us,kgcm}  Units for loads and results.
                        Default: input's, else si.
                          si     kN    kN·m    mm   MPa
                          us     kip   kip·ft  in   psi, ksi
                          kgcm   ton   ton·m   cm   kg/cm2, t/cm2
  --factors {none,csa}  Material reduction factors.
                        Default: input's, else none.
  --initial N,M,V       Initial load, in the units in effect.
                        Default: input's, else 0,0,0.
  --increment N,M,V     Load increment; only signs and ratio matter.
                        0,0,0 solves the initial load alone.
                        Default: input's, else 0,1,0.
                        N: tension positive. M: compression on top positive.
  --more-detail N       Refine the solve N times (more load stages), or
                        max: until Response refines no further.
                        Default: 0.

Output:
  --stage STAGES        Stages for the detail views: peak, all, or numbers
                        and ranges (0,10,20-30 or peak,0-5). 0 is the
                        initial load. Control charts always cover every
                        stage. Default: peak.
  --views VIEWS         Detail views: all, or any of general, cracking,
                        reinforcement, no-shear. Default: all.
  --report              Also write an HTML report: screenshots of the
                        inputs and of the peak stage. Default: off.
  --out DIR             Folder for results. Default: next to each input.
  --stdout              Write the raw record to stdout and no files. One
                        input only; not with --report.
  --overwrite           Replace existing results without asking. Default:
                        ask at a terminal, else stop.

Running:
  -p, --parallel N      Solve up to N inputs at once. Default: 1.
  -q, --quiet           Errors only. Default: off.

Results (NAME is the input file name, or newbeam without one):
  NAME.r2x.txt          Raw record: exported chart data, byte for byte, with
                        versions, input SHA-256 and the settings in effect.
  NAME.r2x.html         Report (--report only).

Exit status: 0 solved · 1 failed · 2 usage error · 3 out of scope

Examples:
  r2x solve
  r2x solve beam.r2t --report
  r2x solve beam.r2t --stage all
  r2x solve beam.r2t --views cracking,no-shear
  r2x solve beam.r2t --increment 0,1,1 --more-detail 2
  r2x solve col.rsp --units si --initial -2000,0,0 --increment 0,1,0
  r2x solve cases\*.r2t --out results --parallel 4
  r2x solve beam.r2t --stdout | py parse.py

r2x is unofficial automation of Response-2000, not affiliated with its
authors, and does not check designs. Its results are Response's own, run under
Wine; the engineer who uses them is responsible for that use.
```

- **Settings are overrides.** `--units`, `--factors`, `--initial` and `--increment` are set
  through Response's own dialogs; r2x never edits the input. Loads are N,M,V as Define Loading
  has them, in the units in effect. An option left out keeps the input's value, or Response's
  start-up default (SI, no factors, 0,0,0 and 0,1,0). The settings in effect are read back from
  the dialogs into the record header.
- **The peak** is the stage Response shows when the solve finishes: the largest load of the
  bottom control chart (the largest moment when the increment has one, the largest shear for V
  alone, the largest compression for N alone).
- **More Detail** puts a new stage between every two up to the peak. `--more-detail max` presses
  it until Response refines no further, which it stops doing at 327 stages; a note says if fewer
  presses took effect than you asked for. Stage numbers are the refined solve's.
- **Existing results** are replaced after a yes at the prompt (Enter keeps them), or without
  asking with `--overwrite`. In a script, with no one to ask, r2x stops instead.
- **Exit status** with several inputs is the most serious outcome: failed, then usage error.
  Status 3 is reserved; nothing returns it.

## Defining a section

`r2x` alone starts a session: a prompt at which a section is defined in steps and then solved.

```
PS> r2x
r2x session: define a section, then solve it. help lists the commands.
r2x> define quick
  File name [new-cross-section.r2t]: pier-cap.r2t
  General Information
    Title [New Cross Section]: Pier cap
    Analysis By []: JM
  Material Properties
    Concrete Cylinder Strength (MPa) [35.0]: 40
    ...
  Shape [Rectangle]
    1) Rectangle  2) Circular  3) T-Beam  4) I-Beam
  > t
  btop (mm) [250]: 900
  ...
  set: General Information: Title Pier cap; Analysis By JM
       Material Properties: Concrete Cylinder Strength 40 MPa
       Shape T-Beam; btop 900 mm; h 1200 mm
  saved pier-cap.r2t, report pier-cap.r2x.html updated (6.3 s)
r2x> define long add web
r2x> solve --increment 0,1,1
r2x> undo
r2x> quit
```

What a `define` sets:

| Noun | Sets |
|---|---|
| `quick` | a new section from its basic properties (Response's Quick Define) |
| `general` | title, comments, analysis by, date, crack spacing, moment axis |
| `materials` | f'c, fy, fpu |
| `section` | the concrete shape and its dimensions |
| `long`, `trans`, `tendons` | longitudinal layers, stirrups, tendon layers: each `add`, `modify` or `delete`, then the name |
| `loads` | constant loads and increments |
| `units`, `factors` | units; material factors |

`help define NOUN` lists a noun's questions.

- **The questions are Response's own fields**, in its order and words, each showing the value
  the section has now in brackets. **Enter keeps it**, and a field is touched only when your
  answer differs. Fields that belong together are asked under their heading (Top
  Non-Prestressed Reinforcement, or Outer Non-Prestressed Reinforcement Ring for a circle);
  choices are listed under their question, and you can type the number or the start of the
  name.
- **Response checks the values.** Its questions and messages come through word for word (an fy
  that would overwrite detailed material properties, a layer name that exists), and a bar it
  does not know brings up its list of bars to choose from. r2x checks only that a number is a
  number.
- **The file is the section; arguments are the analysis.** Each step opens the file in
  Response, sets one part of the section, and Response saves the file. `solve` takes `r2x
  solve`'s options and never changes the file. Loads, units and factors can go either way.
- **The report is the preview.** Every step rewrites `NAME.r2x.html` beside the file with
  Response's input screen, and the page reloads itself; after a `solve` it has the outputs too,
  until the next define takes them out. The session opens it in your browser the first time;
  `report` opens it again. **Put the terminal and the browser side by side**: a page cannot bring
  its own window forward, so when it changes while you are not looking, its title says so
  (`● Solved` or `● Updated`, in the tab and the taskbar) until you look at it.
- **Repeated steps and solves overwrite** the file, its report and its record, as saving does
  in Response. To keep a version, copy the file. `undo` goes back one step (except a step that
  made a new file).
- **Stopping mid-step:** Ctrl+C stops the step and nothing is saved; at the `r2x>` prompt it
  just gives a new prompt (`quit` leaves). A wrong answer can also be fixed with `<`, by
  finishing the step and running the define again, or with `undo`.
- **On the command line**, each define names its file last: `r2x define quick pier-cap.r2t`
  makes it (asking first if it exists), `r2x define long add web pier-cap.r2t` opens it, asks
  and saves it back. Answers can be piped, one per line; that is for tests, not automation
  (a script that writes the input file is the way to automate).

Each step is one container run, about 3 to 7 s.

## Results

### The record, `NAME.r2x.txt`

One text file per input: a header, then each chart's Copy Chart Data text exactly as Response
gave it. The header says where it came from: r2x's, Wine's and `r2k.exe`'s versions,
`response-verified` and `response-files-sha256` (your program folder), the input's name and
SHA-256, the settings in effect, the stage count, the peak, the stages exported, and the
disclaimer. Read it as bytes, and don't open and save it in an editor: `docs/raw-format.md`
has the layout and a small Python reader.

### The report, `NAME.r2x.html`

Screenshots for checking by eye that Response was given what you meant: under **Inputs**,
Response's input screen (and, for a solve, the units and material factors and the loads as r2x
set them); under **Outputs**, Response's window in each view at the peak. No data: that is in
the record. The screenshots are drawn under Wine, so fonts and line weights can differ slightly
from Windows.

The input screen shows a good deal: section properties, the layers with their bars and a
tendon's prestrain, stirrups, cover, crack spacing, a moment axis away from the centroid, the
loads, and the materials' key values. **It does not show** bar and tendon depths as numbers
(the layers are drawn to scale), a tendon's slope, or the material factors (a solve's report
shows them, in Preferences); and the outputs are at the peak only. Check those in Response if
they matter.

## What has been verified

Each reference case was solved in Response on Windows and its charts copied by hand, sharing no
code with r2x. r2x's record matches every one byte for byte:

| Case | Settings | Stages, peak |
|---|---|---|
| Newbeam (250 × 600 rectangle, 3–25M / 1–20M) | moment increment; every view at stages 56 and 36 | 60, peak 56 |
| Newbeam, US units | `--units us` | 60, peak 56 |
| Newbeam, CSA factors | `--factors csa` | 57, peak 46 |
| Newbeam, axial load | `--initial=-2000,0,0` | 46, peak 37 |
| Newbeam, axial increment only | `--increment=-1,0,0` | 35, peak 22 |
| No input (File > New) | none | 60, peak 56 |
| Newbeam, moment and shear (M/V = 1 m) | `--increment 0,1,1`; every view at stages 30 and 20 | 43, peak 30 |
| Newbeam, shear alone | `--increment 0,0,1`; every view | 52, peak 16 |
| Newbeam, More Detail twice | `--more-detail 2`; every view | 228, peak 224 |

One known exception: two exports of the moment-and-shear case at stage 20 each have one zero
printed with the opposite sign (`-0.0000` against `0.0000`), floating-point noise under Wine.

Defining a section: under Wine, Enter through every question of `define quick` gives Newbeam's
file byte for byte, and each dialog's answers land where Response saves them; on Windows, five
sections made by hand and by r2x from the same answers match.

Everything else relies on r2x's own checks: each stage is identified from its strain profile
against the control curves before it is copied, and a chart that appears in several views must
export the same bytes in each. `docs/risk-register.md` lists what could still make a result
differ from Response on Windows, and what is being checked next.

## Troubleshooting

- **"Response-2000 is not linked"**: run `r2x setup --response FOLDER`.
- **"not a build of Response-2000 that r2x has been checked against"**: your `r2k.exe` is
  another version. See *Your copy of Response-2000*.
- **"no image ... here"**: run `r2x setup`, which pulls it.
- **`--stdout` into another program in Windows PowerShell 5.1** can re-encode the record and
  break it. Write a file, or use PowerShell 7.4 or later.
- **Docker in another WSL distribution**: set `R2X_WSL_DISTRO`. To run docker some other way
  (`sudo docker`, Docker Desktop), set `R2X_DOCKER` to the command.

## Citing Response-2000

Response-2000 is free software by Evan C. Bentz and Michael P. Collins, available from
[hadrianworks.com](https://www.hadrianworks.com/). The authors ask that work using it cite
Bentz's PhD thesis: E. C. Bentz, *Sectional Analysis of Reinforced Concrete Members*, University
of Toronto, 2000.

## Disclaimer

r2x is unofficial software that automates Response-2000. It is not affiliated with or endorsed
by Response-2000's authors or the University of Toronto. It runs your own copy of Response-2000
under Wine and returns Response's exported results without checking, changing or interpreting
them.

Those results have been compared with Response running on Windows only for the cases under
*What has been verified*; anything else relies on r2x's own consistency checks, which cannot
catch every way a result could differ. r2x does not check designs. As with any analysis
software, the engineer who uses its results is responsible for judging whether they are fit for
that use.

r2x is provided under the MIT License, without warranty of any kind.
