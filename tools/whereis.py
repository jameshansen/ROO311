#!/usr/bin/env python3
"""Name the module and source line behind an address in a built ROM.

    python3 tools/whereis.py build/A5000 0x03831E4C [more addresses]
    python3 tools/whereis.py build/A5000 --list            the module table

Uses the ROM image and the ELF files the build leaves beside it (AsAsm -G keeps line numbers).
"""
import struct
import subprocess
import sys
from pathlib import Path

BASE = 0x03800000


def modules(rom):
    """(address, length, title) of the kernel's utility module and every module after it."""
    d = rom.read_bytes()
    out, p = [], None
    # the chain starts at the length word in front of the UtilityModule header: find it by walking candidates
    for q in range(0, 0x40000, 4):
        ln = struct.unpack_from("<I", d, q)[0]
        if 0x1000 < ln < 0x80000 and d[q + 4 + struct.unpack_from("<I", d, q + 20)[0]:][:13] == b"UtilityModule":
            p = q
            break
    while p is not None:
        ln = struct.unpack_from("<I", d, p)[0]
        if not ln:
            break
        t = p + 4 + struct.unpack_from("<I", d, p + 20)[0]
        out.append((BASE + p + 4, ln - 4, d[t:d.index(b"\0", t)].decode("latin-1")))
        p += ln
    return out


def main():
    build = Path(sys.argv[1])
    mods = modules(build / "rom")
    if sys.argv[2] == "--list":
        for a, ln, t in mods:
            print(f"{a:08x} {ln:7d} {t}")
        return
    names = {}
    for line in (build.parents[1] / "Sources" / "MODULES").read_text().splitlines():
        f = line.split()
        if len(f) == 3 and not line.startswith(("#", "-")):
            names[f[2]] = f
    for arg in sys.argv[2:]:
        addr = int(arg, 16) & 0x03FFFFFC
        hit = [m for m in mods if m[0] <= addr < m[0] + m[1]]
        if not hit:
            elf, off, title = build / "Kernel.elf", addr, "Kernel"
        else:
            a, ln, title = hit[0]
            # the module file is named in Sources/MODULES, the title comes from its header: match on size
            match = [n for n in names if (build / n).exists() and (build / n).stat().st_size == ln]
            elf, off = (build / f"{match[0]}.elf", addr - a) if match else (build / "Kernel.elf", addr)
            if title == "UtilityModule":
                elf, off = build / "Kernel.elf", addr
        r = subprocess.run(["arm-none-eabi-addr2line", "-e", str(elf), f"{off:#x}"], capture_output=True, text=True)
        where = r.stdout.strip().split("/Sources/")[-1]
        print(f"{addr:08x}: {title} +{addr - (hit[0][0] if hit else BASE):#x}  {where}")


if __name__ == "__main__":
    main()
