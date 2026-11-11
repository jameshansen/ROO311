#!/usr/bin/env python3
"""Join the kernel and the modules into a ROM image.

    python3 tools/mkrom.py <output> <size in K> <kernel> [module ...]

The kernel image ends with a zero word, the end of the module chain. Each module goes in ahead of
that as a length word (the offset to the next entry) and the module itself, padded to a word.
"""
import struct
import sys


def main():
    out, size, kernel, *modules = sys.argv[1:]
    size = int(size) * 1024
    rom = bytearray(open(kernel, "rb").read())
    assert rom[-4:] == b"\0\0\0\0", "kernel does not end with the chain terminator"
    del rom[-4:]
    for m in modules:
        d = open(m, "rb").read()
        d += b"\0" * (-len(d) & 3)
        rom += struct.pack("<I", len(d) + 4) + d
    rom += b"\0\0\0\0"
    assert len(rom) <= size, f"image is {len(rom)} bytes, over the {size} byte ROM"
    print(f"{out}: {len(rom)} bytes used of {size}, {len(modules)} modules after the kernel")
    rom += b"\xff" * (size - len(rom))
    open(out, "wb").write(rom)


if __name__ == "__main__":
    main()
