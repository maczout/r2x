import re, sys
def norm(b): return re.sub(rb"\r*\n|\r", b"\n", b)
a, b = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read()
na, nb = norm(a), norm(b)
if na == nb:
    print(f"IDENTICAL (ignoring line endings)  {sys.argv[1]}  {len(na)} bytes"); sys.exit(0)
la, lb = na.split(b"\n"), nb.split(b"\n")
for i, (x, y) in enumerate(zip(la, lb)):
    if x != y: print(f"DIFF at line {i+1}:\n  wine:    {x!r}\n  windows: {y!r}"); break
else: print(f"DIFF: lengths {len(la)} vs {len(lb)} lines")
sys.exit(1)
