import sys, time
from spike import *

def parse_xy(path):
    pts = []
    for line in open(path, "rb").read().decode("latin-1").splitlines():
        p = line.split()
        if len(p) == 2:
            try: pts.append((float(p[0]), float(p[1])))
            except ValueError: pass
    return pts

mphi = parse_xy("out/control_2.a")
def stage(names):
    copy_chart(names["grid_r1c2"], "out/_s")
    pts = parse_xy("out/_s.a")
    (et, yt), (eb, yb) = pts[1], pts[-2]
    phi = (eb - et) / (yt - yb) * 1000.0
    i = min(range(len(mphi)), key=lambda j: abs(mphi[j][0] - phi))
    return i, round(phi, 3)

names = charts()
main = w("main").strip()
how = sys.argv[1]
def press(vk, xname):
    if how == "post": w("key", main, vk)
    else: xkey(xname)
    time.sleep(0.3)
print("start", stage(names))
for vk, xn in [("0x21", "Prior")] * 3 + [("0x22", "Next")] * 6:
    press(vk, xn); print(xn, stage(names))
