"""Throwaway Wine spike: export both control curves + 5 No Shear charts, then test stage stepping."""
import os, re, subprocess, sys, time

ENV = dict(os.environ, DISPLAY=":99", WINEPREFIX="/home/claude/spike/prefix", WINEDEBUG="-all")


def w(*args):
    r = subprocess.run(["wine", "/home/claude/spike/w32.exe", *args], env=ENV,
                       capture_output=True, text=True)
    return r.stdout.replace("\r", "")


def xkey(*keys):
    subprocess.run(["xdotool", "key", *keys], env=ENV, check=True)


def windows():
    out = []
    for line in w("tree").splitlines():
        m = re.match(r"(\w+) parent=(\w+) vis=(\d) id=(-?\d+) rect=(-?\d+),(-?\d+),(-?\d+),(-?\d+) class=(\S+) text=(.*)", line)
        if m:
            h, p, vis, _id, l, t, r, b, cls, txt = m.groups()
            out.append(dict(h=h, vis=vis == "1", rect=tuple(map(int, (l, t, r, b))), cls=cls, text=txt))
    return out


def charts():
    ws = [x for x in windows() if x["vis"]]
    grid = [x for x in ws if x["cls"] == "OWL_Window" and x["text"] == ""
            and x["rect"][2] - x["rect"][0] > 300 and x["rect"][3] - x["rect"][1] > 200]
    grid.sort(key=lambda x: (round(x["rect"][1] / 50), x["rect"][0]))
    ctrl = sorted([x for x in ws if x["cls"] == "OWL_Window:F" and x["text"].startswith("Control")],
                  key=lambda x: x["rect"][1])
    names = {f"grid_r{i // 3 + 1}c{i % 3 + 1}": x["h"] for i, x in enumerate(grid)}
    names.update({f"control_{i + 1}": x["h"] for i, x in enumerate(ctrl)})
    return names


def copy_chart(hwnd, base, downs=2):
    w("clipclear")
    seq0 = int(w("clipseq"))
    w("rclick", hwnd)
    t0 = time.time()
    while "none" in w("popup"):
        if time.time() - t0 > 3:
            raise RuntimeError("popup did not appear")
        time.sleep(0.05)
    xkey(*["Down"] * downs, "Return")
    t0 = time.time()
    while int(w("clipseq")) == seq0:
        if time.time() - t0 > 3:
            raise RuntimeError("clipboard did not change")
        time.sleep(0.05)
    w("clip", base)
    return time.time()


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    names = charts()
    print(names)
    for name in ["control_1", "control_2", "grid_r1c2", "grid_r1c3", "grid_r2c2", "grid_r2c3", "grid_r3c1"]:
        t0 = time.time()
        copy_chart(names[name], f"out/{name}")
        print(f"{name}: {time.time() - t0:.2f} s")
