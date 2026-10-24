import sys, struct, pefile
pe = pefile.PE(sys.argv[1])
def items(data):
    pos = 4 + struct.unpack_from("<HH", data, 0)[1]
    while pos + 2 <= len(data):
        flags, = struct.unpack_from("<H", data, pos); pos += 2
        mid = None
        if not flags & 0x10:
            mid, = struct.unpack_from("<H", data, pos); pos += 2
        s = pos
        while data[pos:pos+2] != b"\0\0": pos += 2
        text = data[s:pos].decode("utf-16le"); pos += 2
        yield flags, mid, text
for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if t.id != 4: continue
    for n in t.directory.entries:
        for l in n.directory.entries:
            d = pe.get_data(l.data.struct.OffsetToData, l.data.struct.Size)
            print(f"=== MENU {n.id if n.id is not None else n.name}")
            for f, mid, text in items(d):
                print(("POPUP " if f & 0x10 else f"{mid:6d} ") + repr(text) + ("  [END]" if f & 0x80 else ""))
