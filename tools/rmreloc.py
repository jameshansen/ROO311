#!/usr/bin/env python3
"""A relocatable module from a C module linked twice, with tools/reloc.s in it.

    python3 tools/rmreloc.py <linked at 0> <linked at 0x10000> <ELF of the first> <out>

The words that differ by exactly &10000 between the two links are the addresses in the module, and
their offsets from __RelocCode become the table reloc.s works through when the module starts. Any other
difference is an address the table can't fix, and stops the build. The module's static data is copied
to its workspace after relocation, so an address in it that points into that data would still point at
the module's own copy: those are listed and stop the build too.
"""
import subprocess
import sys

SHIFT = 0x10000


def symbols(elf):
    out = {}
    for line in subprocess.run(["arm-none-eabi-nm", elf], capture_output=True, text=True, check=True).stdout.splitlines():
        parts = line.split()
        if len(parts) == 3:
            out[parts[2]] = int(parts[0], 16)
    return out


def main():
    a, b = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read()
    sym = symbols(sys.argv[3])
    if len(a) != len(b):
        sys.exit("rmreloc: the two links differ in length")
    a = bytearray(a)
    rw_base, rw_limit = sym["Image$$RW$$Base"], sym["Image$$RW$$Limit"]
    code = sym["__RelocCode"]
    offsets, bad, inner = [], [], []
    for i in range(0, len(a) - 3, 4):
        x, y = int.from_bytes(a[i:i + 4], "little"), int.from_bytes(b[i:i + 4], "little")
        if x == y:
            continue
        if (y - x) & 0xFFFFFFFF != SHIFT:
            bad.append(i)
            continue
        offsets.append(i)
        if rw_base <= i < rw_limit and rw_base <= x < rw_limit:
            inner.append(i)
    if bad or inner:
        for i in bad:
            print("rmreloc: word at &%X changes by something other than &%X" % (i, SHIFT))
        for i in inner:
            print("rmreloc: static at &%X holds the address of another static" % i)
        sys.exit(1)
    table = len(a) + (-len(a) % 4)
    a += bytes(table - len(a))
    for i in offsets:
        a += ((i - code) & 0xFFFFFFFF).to_bytes(4, "little")
    a += (0xFFFFFFFF).to_bytes(4, "little")
    a[sym["RelocWhere"]:sym["RelocWhere"] + 4] = code.to_bytes(4, "little")
    a[sym["RelocTable"]:sym["RelocTable"] + 4] = (table - code).to_bytes(4, "little")
    open(sys.argv[4], "wb").write(a)
    print("%s: %d bytes, %d relocations" % (sys.argv[4], len(a), len(offsets)))


if __name__ == "__main__":
    main()
