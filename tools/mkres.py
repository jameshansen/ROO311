#!/usr/bin/env python3
"""Gather the components' resource files into the data block of the Messages module.

    python3 tools/mkres.py <output file> <locale> <component folder> [more folders]
    python3 tools/mkres.py --list <locale> <component folder> ...      show what would go in

Each component's Makefile has a "resources" target that copies its messages, templates and sprites
into the ROM's resource tree:
    ${CP} Resources.${LOCALE}.Messages  ${RESDIR}.${COMPONENT}.Messages  ${CPFLAGS}
This runs those copies in memory and writes the result in the form ResourceFS registers (the layout of
the ResourceFile macro in Hdr:ResourceFS): for each file an offset to the next, load and exec addresses,
length, access, name, length + 4, data; then a zero word.

A file's type comes from a ",xxx" suffix on its name, or from the usual names (Templates, Sprites),
or else it is text. Date stamps are zero so the same sources always give the same ROM.

The message files are then tokenised as the original build tokenised them (tools/msgtok.py).
"""
import re
import struct
import sys
from pathlib import Path

TYPES = {"templates": 0xFEC, "sprites": 0xFF9, "sprites22": 0xFF9, "sprites23": 0xFF9, "tools": 0xFF9, "!sprites": 0xFF9,
         "!sprites22": 0xFF9, "!sprites23": 0xFF9, "!boot": 0xFEB, "!run": 0xFEB, "!runimage": 0xFF8}


def find(base, parts):
    """The file or folder under base named by RISC OS path parts, whatever its case or ,xxx suffix."""
    p = base
    for part in parts:
        if part in ("^",):
            p = p.parent
            continue
        hit = [c for c in p.iterdir() if c.name.lower() == part.lower() or re.fullmatch(re.escape(part) + r",[0-9a-f]{3}", c.name, re.I)] if p.is_dir() else []
        if not hit:
            return None
        p = hit[0]
    return p


def leaf(path):
    m = re.fullmatch(r"(.*),([0-9a-fA-F]{3})", path.name)
    return (m.group(1), int(m.group(2), 16)) if m else (path.name, TYPES.get(path.name.lower(), 0xFFF))


def variables(make, overrides):
    v = {}
    for line in make.read_text(encoding="latin-1").splitlines():
        m = re.match(r"([A-Za-z_0-9]+)\s*\??=\s*(.*)", line)
        if m:
            v.setdefault(m.group(1), m.group(2).strip())
    v.update(overrides)
    return v


def expand(s, v):
    for _ in range(10):
        new = re.sub(r"\$[{(]([A-Za-z_0-9]+)[})]", lambda m: v.get(m.group(1), ""), s)
        if new == s:
            break
        s = new
    return s


def add(files, src, dst):
    if src.is_dir():
        for c in sorted(src.iterdir()):
            if not c.name.startswith("."):
                add(files, c, dst + "." + leaf(c)[0])
    else:
        files[dst] = (src.read_bytes(), leaf(src)[1])


def gather(comp, locale, files, missing):
    make = comp / "Makefile"
    if not make.exists():
        return
    v = variables(make, {"LOCALE": locale, "CP": "copy", "MKDIR": "cdir"})
    # RESDIR is handed down by the ROM build as the Resources folder of the tree. A Makefile that sets it
    # to a folder of its own (the Messages module's staging area) means the root of the tree.
    v["RESDIR"] = "<resource$dir>" if "RESDIR" in v and "resource$dir" not in v["RESDIR"] else v.get("RESDIR", "<resource$dir>.Resources")
    inside, before = False, len(files)
    for line in make.read_text(encoding="latin-1").splitlines():
        if re.match(r"resources[^:]*:", line):
            inside = True
            continue
        if inside and line[:1] not in ("\t", " ", "", "#"):
            inside = False
        f = expand(line, v).split()
        if not inside or len(f) < 3 or f[0] != "copy":
            continue
        dst = f[2].replace("<resource$dir>.", "").replace("<Resource$Dir>.", "")
        if f[1].endswith(".*"):
            src = find(comp, f[1][:-2].split("."))
            dst = dst[:-2] if dst.endswith(".*") else dst
        else:
            src = find(comp, f[1].split("."))
        if src is None:
            missing.append(f"{comp.name}: {f[1]}")
        else:
            add(files, src, dst)
    # The current sources leave the copying to shared makefiles: a component's Resources/<locale> folder
    # goes to Resources.<COMPONENT>
    res = find(comp, ["Resources", locale])
    if len(files) == before and res is not None and v.get("COMPONENT"):
        add(files, res, "Resources." + v["COMPONENT"])


def block(files):
    out = bytearray()
    for name, (data, ftype) in files.items():
        head = struct.pack("<IIII", 0xFFF00000 | ftype << 8, 0, len(data), 3) + name.encode("latin-1") + b"\0"
        head += b"\0" * (-len(head) & 3)
        body = struct.pack("<I", len(data) + 4) + data
        body += b"\0" * (-len(body) & 3)
        out += struct.pack("<I", 4 + len(head) + len(body)) + head + body
    return bytes(out)


def main():
    out, locale, *comps = sys.argv[1:]
    files, missing = {}, []
    for c in comps:
        gather(Path(c), locale, files, missing)
    for m in missing:
        print(f"mkres: not found: {m}", file=sys.stderr)
    import msgtok
    print(f"tokenising the messages saved {msgtok.tokenise(files)} bytes")
    if out == "--list":
        for name, (data, ftype) in files.items():
            print(f"{ftype:03x} {len(data):7d} {name}")
    else:
        Path(out).write_bytes(block(files))
    print(f"{len(files)} resource files, {sum(len(d) for d, _ in files.values())} bytes")


if __name__ == "__main__":
    main()
