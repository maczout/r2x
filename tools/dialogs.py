"""python tools/dialogs.py r2k.exe — list the dialog templates (RT_DIALOG) in a Windows binary.

Response-2000's dialogs are built from these templates, so the control IDs printed here are the
ones the worker addresses (by GetDlgItem), rather than screen positions. Needs pefile.
"""

from __future__ import annotations

import struct
import sys

import pefile

CLASSES = {0x80: "Button", 0x81: "Edit", 0x82: "Static", 0x83: "ListBox", 0x84: "ScrollBar",
           0x85: "ComboBox"}
BUTTON_KINDS = {0: "push", 1: "default", 2: "checkbox", 3: "auto-checkbox", 4: "radio",
                5: "3state", 6: "auto-3state", 7: "groupbox", 9: "auto-radio", 11: "owner-draw"}


class Reader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def take(self, fmt: str):
        values = struct.unpack_from("<" + fmt, self.data, self.pos)
        self.pos += struct.calcsize("<" + fmt)
        return values if len(values) > 1 else values[0]

    def string(self) -> str:
        end = self.pos
        while self.data[end:end + 2] != b"\0\0":
            end += 2
        text = self.data[self.pos:end].decode("utf-16le")
        self.pos = end + 2
        return text

    def sz_or_ord(self):
        first = self.take("H")
        if first == 0:
            return ""
        if first == 0xFFFF:
            return self.take("H")
        self.pos -= 2
        return self.string()

    def align(self):
        self.pos = (self.pos + 3) & ~3


def parse(data: bytes) -> tuple[str, list[dict]]:
    r = Reader(data)
    ex = struct.unpack_from("<HH", data, 0) == (1, 0xFFFF)
    if ex:
        r.take("HHIII")
        style = struct.unpack_from("<I", data, 12)[0]
    else:
        style = r.take("I")
        r.take("I")
    count = r.take("H")
    r.take("hhhh")
    r.sz_or_ord()
    r.sz_or_ord()
    title = r.string()
    if style & 0x40:  # DS_SETFONT
        r.take("H")
        if ex:
            r.take("HBB")
        r.string()
    items = []
    for _ in range(count):
        r.align()
        if ex:
            _, _, istyle = r.take("III")
            x, y, cx, cy = r.take("hhhh")
            cid = r.take("i")
        else:
            istyle, _ = r.take("II")
            x, y, cx, cy = r.take("hhhh")
            cid = r.take("H")
        cls = r.sz_or_ord()
        text = r.sz_or_ord()
        extra = r.take("H")
        r.pos += extra
        cls = CLASSES.get(cls, cls) if isinstance(cls, int) else cls
        kind = BUTTON_KINDS.get(istyle & 0xF, f"style {istyle & 0xF}") if cls == "Button" else ""
        items.append({"id": cid if cid != 0xFFFF else -1, "class": cls, "kind": kind,
                      "text": text, "rect": (x, y, cx, cy)})
    return title, items


def main(path: str):
    pe = pefile.PE(path)
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id != 5:  # RT_DIALOG
            continue
        for n in t.directory.entries:
            for lang in n.directory.entries:
                d = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                name = n.id if n.id is not None else str(n.name)
                title, items = parse(d)
                print(f"=== DIALOG {name} {title!r}")
                for it in items:
                    x, y, cx, cy = it["rect"]
                    label = f"{it['class']}" + (f"/{it['kind']}" if it["kind"] else "")
                    print(f"  {it['id']:6d}  {label:22s} {it['text']!r:40s} @{x},{y} {cx}x{cy}")


if __name__ == "__main__":
    main(sys.argv[1])
