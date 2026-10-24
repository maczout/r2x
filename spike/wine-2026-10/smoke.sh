#!/usr/bin/env bash
# Repeat the Wine spike in a fresh Linux environment (e.g. WSL) and compare the seven exports with
# the hand-captured references in tests/reference/newbeam.
#
#   bash spike/wine-2026-10/smoke.sh
#
# Needs: wine (32-bit), xvfb, xdotool, x11-utils, mingw-w64, python3; Response-2000 in ./Response.
# Works in $R2X_DEV (default ~/r2x-dev), never in the repo: Response runs from a copy there, so the
# Windows copy's Response.ini is left alone.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
RESPONSE_SRC=${RESPONSE_DIR:-$REPO/Response}
CASE=$REPO/tests/reference/newbeam
WORK=${R2X_DEV:-$HOME/r2x-dev}

export WINEPREFIX=$WORK/prefix WINEARCH=win32 WINEDEBUG=-all
export DISPLAY=${SMOKE_DISPLAY:-:99}
export W32_EXE=$WORK/w32.exe

[ -f "$RESPONSE_SRC/r2k.exe" ] || { echo "no r2k.exe in $RESPONSE_SRC" >&2; exit 1; }
mkdir -p "$WORK"
rm -rf "$WORK/Response" "$WORK/out"
cp -r "$RESPONSE_SRC" "$WORK/Response"
cp "$CASE/input.r2t" "$WORK/Newbeam.r2t"
echo "wine:    $(wine --version)"
echo "r2k.exe: $(sha256sum "$WORK/Response/r2k.exe" | cut -d' ' -f1)"

i686-w64-mingw32-gcc -O1 -o "$W32_EXE" "$HERE/w32.c" -luser32

XVFB_PID=
if ! xdpyinfo >/dev/null 2>&1; then
    Xvfb "$DISPLAY" -screen 0 1920x1080x24 >/dev/null 2>&1 &
    XVFB_PID=$!
    sleep 1
fi
cleanup() { wineserver -k 2>/dev/null || true; [ -n "$XVFB_PID" ] && kill "$XVFB_PID" 2>/dev/null || true; }
trap cleanup EXIT

[ -d "$WINEPREFIX" ] || { echo "creating Wine prefix (first run only, ~1 min)"; wineboot -i >/dev/null 2>&1; }

w32() { wine "$W32_EXE" "$@" 2>/dev/null | tr -d '\r'; }
wait_for() {  # wait_for <seconds> <command...>
    local t=$1; shift
    for _ in $(seq $((t * 4))); do "$@" >/dev/null 2>&1 && return 0; sleep 0.25; done
    echo "timed out: $*" >&2; return 1
}

(cd "$WORK/Response" && nohup wine r2k.exe "$(winepath -w "$WORK/Newbeam.r2t")" >/dev/null 2>&1 &)
wait_for 60 w32 main
echo "opened"

w32 cmd 5092                                           # Solve -> Sectional Response
wait_for 30 bash -c "wine '$W32_EXE' tree 2>/dev/null | grep -q 'vis=1.*text=Control'"
sleep 1
echo "solved"

python3 "$HERE/spike.py" "$WORK/out"

fail=0
while read -r ref got; do
    if cmp -s "$CASE/$ref" "$WORK/out/$got.a"; then echo "IDENTICAL  $ref"
    else echo "DIFFERS    $ref"; fail=1; fi
done <<'EOF'
control/moment_ex.txt control_1
control/moment_phi.txt control_2
stages/056/longitudinal_strain.txt grid_r1c2
stages/056/shrinkage_thermal_strain.txt grid_r1c3
stages/056/long_reinforcement_stress.txt grid_r2c2
stages/056/long_reinf_stress_at_crack.txt grid_r2c3
stages/056/longitudinal_concrete_stress.txt grid_r3c1
EOF
[ $fail = 0 ] && echo "SMOKE TEST PASSED" || { echo "SMOKE TEST FAILED (exports in $WORK/out)"; exit 1; }
