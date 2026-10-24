# Wine spike, 2026-10-24

Question: does an unmodified Response-2000 run under Wine on Linux and export the same chart data
as it does on Windows? **Answer: yes.** Throwaway code is in `spike/wine-2026-10/`.

## Setup

- Ubuntu 24.04, Wine `9.0~repack-4build3` (Ubuntu package), 32-bit prefix (`WINEARCH=win32`),
  `Xvfb :99 -screen 0 1920x1080x24`, no window manager.
- Response-2000 1.9.7, `r2k.exe` SHA-256
  `bbf4bc595ee80167ea73a76d597b2223cbc5e9c47d97d452025cde4bb85e4e74`, with the DLLs from its program
  folder (OWL 6.42, MSVC 14 runtime). No winetricks or native DLL overrides were needed.
- Input: `Newbeam.r2t` (same file as `tests/reference/newbeam/input.r2t`).

## Results

| Check | Result |
|---|---|
| `wine r2k.exe <path.r2t>` opens the file | Works; title `Response  -  newbeam  -  New Cross Section` |
| Solve → Sectional Response (`WM_COMMAND` 5092 posted to the main window) | Works; No Shear view, opens on the maximum-moment stage (56 of 0–59) |
| Copy Chart Data, both control curves + 5 No Shear charts at that stage | All 7 identical to the Windows export (probe, pywinauto), ignoring line endings |
| PgUp / PgDn (`WM_KEYDOWN` posted to the main window) | Same stage sequence as on Windows; clamps at 0 and 59 |

Windows reference for the comparison was the earlier pywinauto probe output, not hand copies.
Hand copies made later (`tests/reference/newbeam/`) are byte-identical to the Wine exports,
including CRLF line endings.

## Findings that shape the worker

- **Automation from inside Wine.** A small Win32 C program (`w32.c`, built with
  `i686-w64-mingw32-gcc`) runs in the same prefix and can enumerate Response's windows, post
  messages and read the clipboard with `GetClipboardData`. Linux-side Python drives it.
- **Menus.** Wine cannot read another process's menus (`GetMenuItemCount` fails cross-process).
  Main menu command IDs are fixed in the exe's `RT_MENU` resource (`menus.txt`):
  Sectional Response `5092`, More Detail `11845`, Next Load Stage `4501` (PgUp),
  Previous Load Stage `4500` (PgDn).
- **Chart context menus** are built at runtime, so their IDs are unknown. The spike right-clicks
  the chart by posted messages, then selects Copy Chart Data with real keys
  (`xdotool key Down Down Return`). Same item order for grid and control charts. This is the most
  fragile step; check the `Title :` line of each export against the expected chart.
- **Clipboard text** is ASCII with CRLF line endings; CF_TEXT and CF_UNICODETEXT carry identical
  text. Greek letters are spelled `|e_x`, `|f`. Completion can be detected with
  `GetClipboardSequenceNumber`.
- **Chart windows:** grid charts are untitled `OWL_Window` children of the client area (sort
  row-major); control charts are `OWL_Window:F` with window text `Control : M-Phi` (both of them;
  the real title is only in the export). Top control chart = Moment–εx, bottom = Moment–φ.
- **Stage identification:** Response shows no stage number. The spike derived curvature from the
  Longitudinal Strain export and matched it to the Moment–φ curve. Traversal that works for any
  opening stage: page down until it stops (stage 0), then page up through every stage.
- **Timing:** ~0.85 s per chart. Much of it is starting a new helper process per call.

## Loose ends

- Solve completion was a fixed 2 s sleep; needs a real wait condition.
- Symbol font missing in the prefix, so Greek glyphs draw as boxes on screen. Cosmetic.
- Wine logs `Failed to start RpcSs service` and a timezone fixme; harmless here.
