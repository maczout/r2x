# r2x

Run Response-2000 from the command line.

r2x drives your own copy of Response-2000, Bentz and Collins' sectional analysis program for
reinforced and prestressed concrete, under Wine in a Linux container. It solves sections and
returns Response's own exported data, byte for byte, without re-computing, filtering or
interpreting anything; and it defines sections question by question through Response's own
dialogs.

> r2x is unofficial and does not check designs. See *Disclaimer*, below.

**Scope:** the sectional response to axial load, moment and shear (Solve > Sectional
Response), optionally refined with More Detail: both control charts, and every chart with a
data export in four detail views (General, Cracking, Reinforcement, No Shear). Not M–N, M–V or
N–V interaction, and not full-member analysis.

## Quick start (Windows)

1. WSL 2 with Ubuntu 24.04, and Docker Engine inside it: `sudo apt-get install docker.io
   docker-buildx`, then `sudo usermod -aG docker $USER` and reopen Ubuntu.
2. Python 3.10+ in Windows, then r2x:
   `py -m pip install https://github.com/maczout/r2x/archive/refs/tags/v0.5.0.zip`
3. Response-2000 from [hadrianworks.com](https://www.hadrianworks.com/), installed as usual.
4. Link it and get the image (about 1.3 GB, once):
   `r2x setup --response "C:\path\to\Response"` (its program folder, with `r2k.exe`).
5. `r2x health` shows the linked Response and the image's versions.

```
PS> r2x solve .\Newbeam.r2t --report
[Newbeam] solved: 60 stages, peak 56 -> Newbeam.r2x.txt, Newbeam.r2x.html (6.2 s)
```

- `NAME.r2x.txt`, **the record**: Response's Copy Chart Data text for both control charts at
  every stage and every detail chart at the peak (or the stages you ask for), behind a header
  that says where it came from.
- `NAME.r2x.html`, **the report** (`--report`): Response's screens, for checking by eye that it
  was given what you meant.

`r2x` alone starts a session in which a section is defined in steps and then solved, with the
report as a preview that updates itself:

```
PS> r2x
r2x> define quick
r2x> define long add web
r2x> solve --increment 0,1,1
```

## Documents

- [`docs/guide.md`](docs/guide.md): the user guide. Installing and linking Response, solving,
  defining a section, reading the results, what has been verified.
- [`docs/raw-format.md`](docs/raw-format.md): the record's layout and a Python reader; r2x's
  contract with whatever reads it.
- [`docs/internals.md`](docs/internals.md): how it works, the tests, releasing.
- [`docs/risk-register.md`](docs/risk-register.md): what could still make a result differ from
  Response on Windows.
- [`docs/history.md`](docs/history.md): the decisions behind r2x and what was found in
  Response along the way. [`docs/dialogs.md`](docs/dialogs.md): every field `define` asks.

## Response-2000

Response-2000 is free software by Evan C. Bentz and Michael P. Collins, available from Bentz's
site, [hadrianworks.com](https://www.hadrianworks.com/). r2x does not include it: you link your
own copy. The authors ask that work using it cite Bentz's PhD thesis: E. C. Bentz, *Sectional
Analysis of Reinforced Concrete Members*, University of Toronto, 2000. Check the authors' terms
before running it as a service for others.

## Disclaimer

r2x is unofficial software that automates Response-2000. It is not affiliated with or endorsed
by Response-2000's authors or the University of Toronto. It runs your own copy of Response-2000
under Wine and returns Response's exported results without checking, changing or interpreting
them.

Those results have been compared with Response running on Windows only for the cases listed in
the user guide, under *What has been verified*; anything else relies on r2x's own consistency
checks, which cannot catch every way a result could differ. r2x does not check designs. As with
any analysis software, the engineer who uses its results is responsible for judging whether
they are fit for that use.

## License

MIT, r2x's code only, without warranty of any kind.
