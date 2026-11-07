# The dialogs r2x define drives

Reference for builders: every field `r2x define` asks, with its control in `r2k.exe` and where
Response saves it. How a step works is in `docs/internals.md`; what was found in Response is in
`docs/history.md`, *Defining a section*.

The survey by `python tools/define_survey.py` (Newbeam: Quick Define's defaults, then
`tests/reference/newbeam/input.r2t` for the others). **Control**: the control ID (RT_DIALOG of
r2k.exe, `docs/r2k-dialogs.txt`); **Frame**: the group box the field sits in, read from the
dialog as the question is asked (`docs/internals.md`, *Frames*); **Question**: the label the
dialog shows, else the catalogue's words; **Precision**: decimals the dialog shows; **Saved
as**: the element and attribute of the saved file. For a list dialog, each item's value
(Tendons: none in Newbeam, so what an Add shows). "(not shown)": a field Newbeam's dialog does
not show (a shape's unused dimensions, disabled; a spacing or axis behind its ticked Automatic
box, which shows "Automatic" or "Centroid" and 0.0 once unticked).

| Noun | Field | Frame | Question | Control | Kind | Newbeam shows | Precision | Saved as |
|---|---|---|---|---|---|---|---|---|
| quick | title | General Information | Title | 5060 | text | New Cross Section | text | r3g_beam name |
| quick | analysis-by | General Information | Analysis By | 5061 | text | (blank) | text | r3g_beam doneby |
| quick | fc | Material Properties | Concrete Cylinder Strength | 5064 | number | 35.0 MPa | 1 dp | concrete fcp |
| quick | fy | Material Properties | Long. Steel Yield Strength | 5031 | number | 400 MPa | 0 dp | rebar fy |
| quick | fyt | Material Properties | Transverse Steel Yield | 5065 | number | 400 MPa | 0 dp | rebar name=Trans fy |
| quick | prestress | Material Properties | Prestressed Steel Type | 5070 | choice | 1860 MPa Low Relaxation 13 mm strands | text | prestress |
| quick | shape | - | Shape | 5025 | shape | Rectangle | text | shapesection name |
| quick | dim1 | - | b | 5060 | number | 250 mm | 0 dp | shapesection par1 |
| quick | dim2 | - | h | 5061 | number | 600 mm | 0 dp | shapesection par2 |
| quick | dim3 | - | Dimension 3 | 5062 | number | (not shown) |  | shapesection par3 |
| quick | dim4 | - | Dimension 4 | 5123 | number | (not shown) |  | shapesection par4 |
| quick | dim5 | - | Dimension 5 | 5064 | number | (not shown) |  | shapesection par5 |
| quick | dim6 | - | Dimension 6 | 101 | number | (not shown) |  | shapesection par6 |
| quick | top-number | Top Non-Prestressed Reinforcement | Number of Bars | 5060 | integer | 1 | 0 dp | longreinfx name=top num |
| quick | top-by-area | Top Non-Prestressed Reinforcement | Select bar by area | 107 | check | n | text | - |
| quick | top-bar | Top Non-Prestressed Reinforcement | Bar Designation | 5061 | bar | 20M | text | longreinfx name=top bartitle |
| quick | bottom-number | Bottom Non-Prestressed Reinforcement | Number of Bars | 5062 | integer | 3 | 0 dp | longreinfx num |
| quick | bottom-by-area | Bottom Non-Prestressed Reinforcement | Select bar by area | 5014 | check | n | text | - |
| quick | bottom-bar | Bottom Non-Prestressed Reinforcement | Bar Designation | 5123 | bar | 25M | text | longreinfx bartitle |
| quick | stirrup-type | Transverse Steel | Stirrup Type | 5004 | choice | T Headed single leg | text | transreinfz pattern |
| quick | stirrup-by-area | Transverse Steel | Select bar by area | 5067 | check | n | text | - |
| quick | stirrup-bar | Transverse Steel | Bar Designation | 5061 | bar | 10M | text | transreinfz bartitle |
| quick | spacing | Transverse Steel | Spacing | 5062 | number | 250 mm | 0 dp | transreinfz space |
| quick | cover | Transverse Steel | Clear Cover | 5065 | number | 40 mm | 0 dp | transreinfz disttop, distbot |
| quick | strands | Bottom Tendons | Number of 13 mm strands | 5041 | integer | 0 | 0 dp | longreinfx num (a tendon layer) |
| quick | prestrain | Bottom Tendons | Delta-Epsilon P | 5044 | number | 6.500 mm/m | 3 dp | longreinfx dep |
| general | title | Title and General Comments | Title | 5032 | first-line | New Cross Section | text | r3g_beam name |
| general | comments | Title and General Comments | Comments | 5032 | other-lines | (blank) | text | r3g_beam name (after the first line) |
| general | analysis-by | Title and General Comments | Analysis By | 5870 | text | (blank) | text | r3g_beam doneby |
| general | date | Title and General Comments | Date | 5050 | text | 2026/10/24 | text | r3g_beam date |
| general | auto-long-spacing | Crack Spacing | Automatic Longitudinal Spacing | 101 | check | y | text | - |
| general | long-spacing | - | Longitudinal Spacing | 5042 | number | (not shown) |  | r3g_beam smx |
| general | auto-trans-spacing | Crack Spacing | Automatic Transverse Spacing | 103 | check | y | text | - |
| general | trans-spacing | - | Transverse Spacing | 5043 | number | (not shown) |  | r3g_beam smt |
| general | centroidal-axis | Moment Axis | Centroidal Moment axis | 5871 | check | y | text | - |
| general | moment-axis | - | Moment axis | 5044 | number | (not shown) |  | r3g_beam axialloc |
| materials | fc | Concrete | Concrete Cylinder Strength | 104 | number | 35.0 MPa | 1 dp | concrete fcp |
| materials | fy | Non Prestressed Reinforcement | Reinforcement Yield Strength | 105 | number | Detailed MPa | text | rebar fy (every type) |
| materials | fpu | Prestressed Reinforcement | Prestressed Reinforcement Strength | 322 | number | 1860 MPa | 0 dp | prestress fu |
| section | shape | - | Shape | 5025 | shape | Rectangle | text | shapesection name, sectionSOLID |
| section | dim1 | - | b | 5060 | number | 250 mm | 0 dp | shapesection par1 |
| section | dim2 | - | h | 5061 | number | 600 mm | 0 dp | shapesection par2 |
| section | dim3 | - | Dimension 3 | 5062 | number | (not shown) |  | shapesection par3 |
| section | dim4 | - | Dimension 4 | 5123 | number | (not shown) |  | shapesection par4 |
| section | dim5 | - | Dimension 5 | 5064 | number | (not shown) |  | shapesection par5 |
| section | dim6 | - | Dimension 6 | 101 | number | (not shown) |  | shapesection par6 |
| long | number | Layer Definition | Number of Bars | 5060 | integer | bot: 3; top: 1 | 0 dp | longreinfx num |
| long | by-area | Layer Definition | Select bar by area | 5084 | check | bot: n; top: n | text | - |
| long | bar | Layer Definition | Bar Designation | 5062 | bar | bot: 25M; top: 20M | text | longreinfx bartitle, A |
| long | depth | Layer Definition | Dist. from Bottom | 5063 | number | bot: 64 mm; top: 539 mm | 0 dp | longreinfx z |
| long | type | Layer Definition | Rebar Type | 5070 | choice | bot: Steel 1; top: Steel 1 | text | longreinfx type |
| trans | spacing | Stirrup Definition | Stirrup Spacing | 5060 | number | stirrup: 250 mm | 0 dp | transreinfz space |
| trans | by-area | Stirrup Definition | Select bar by area | 5084 | check | stirrup: n | text | - |
| trans | bar | Stirrup Definition | Bar Designation | 5062 | bar | stirrup: 10M | text | transreinfz bartitle, A |
| trans | top | Stirrup Definition | Dist. to Top | 5063 | number | stirrup: 554 mm | 0 dp | transreinfz disttop |
| trans | bottom | Stirrup Definition | Dist. to Bottom | 5064 | number | stirrup: 46 mm | 0 dp | transreinfz distbot |
| trans | bar-type | Stirrup Definition | Bar Type | 322 | choice | stirrup: T Headed single leg | text | transreinfz pattern |
| trans | type | Stirrup Definition | Rebar Type | 5070 | choice | stirrup: Trans | text | transreinfz type |
| tendons | number | Layer Definition | Number of Strands | 5060 | integer | (add): (blank) | text | longreinfx num |
| tendons | by-area | Layer Definition | Select bar by area | 5084 | check | (add): n | text | - |
| tendons | strand | Layer Definition | Strand Designation | 5062 | bar | (add): (blank) | text | longreinfx bartitle, A |
| tendons | prestrain | Layer Definition | Prestrain | 5063 | number | (add): (blank) | text | longreinfx dep |
| tendons | depth | Layer Definition | Dist. from Bottom | 5064 | number | (add): (blank) | text | longreinfx z |
| tendons | slope | Layer Definition | Slope of Tendon | 5065 | number | (add): (blank) | text | longreinfx slope |
| tendons | type | Layer Definition | Tendon Type | 5070 | choice | (add): Steel 1 | text | longreinfx type |
| loads | axial | - | Axial Load, Constant | 101 | number | 0.00 kN | 2 dp | sectloading BN |
| loads | moment | - | Moment, Constant | 5052 | number | 0.00 kNm | 2 dp | sectloading BM |
| loads | shear | - | Shear, Constant | 5053 | number | 0.00 kN | 2 dp | sectloading BV |
| loads | axial-increment | - | Axial Load, Increment | 5054 | number | 0.00 kN | 2 dp | sectloading MN |
| loads | moment-increment | - | Moment, Increment | 5055 | number | 1.00 kNm | 2 dp | sectloading MM |
| loads | shear-increment | - | Shear, Increment | 5056 | number | 0.00 kN | 2 dp | sectloading MV |
| units | units | - | Units | 5028/5029/5030 | radio | SI Metric | text | r3g_beam units |
| factors | concrete | Material Factors | Concrete | 5041 | number | 1.00 | 2 dp | analysisoptions phic |
| factors | steel | Material Factors | Steel | 5044 | number | 1.00 | 2 dp | analysisoptions phis |
| factors | prestress | Material Factors | Prestress | 5045 | number | 1.00 | 2 dp | analysisoptions phip |

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
