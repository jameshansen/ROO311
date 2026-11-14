#!/usr/bin/env python3
"""Files for ResourceFS, held in a module, as Acorn's resgen made them.

    python3 tools/resgen.py <function> <out.s> (<file> <ResourceFS name>)...

Writes an assembler source that exports <function>, a C function returning the address of a block of
the files in the form ResourceFS_RegisterFiles takes: for each file the offset to the next, its load
and execution addresses, length and attributes, its name, then its length plus 4 and its contents, each
part padded to a word, and a zero word at the end. A file's type comes from a ,xxx ending of its name
on disc (text otherwise), and its date is fixed, so the block is the same at every build.
"""
import sys

DATE = 36524 * 86400 * 100   # 1 Jan 2000, in centiseconds since 1900


def entry(path, name):
    data = open(path, "rb").read()
    ftype = int(path[-3:], 16) if path[-4:-3] == "," else 0xFFF
    load = 0xFFF00000 | ftype << 8 | (DATE >> 32) & 0xFF
    pad = lambda b: b + b"\0" * (-len(b) % 4)
    body = pad(name.encode("latin-1") + b"\0") + (len(data) + 4).to_bytes(4, "little") + pad(data)
    head = [20 + len(body), load, DATE & 0xFFFFFFFF, len(data), 0x13]
    return b"".join(w.to_bytes(4, "little") for w in head) + body


def main():
    func, out, pairs = sys.argv[1], sys.argv[2], sys.argv[3:]
    block = b"".join(entry(pairs[i], pairs[i + 1]) for i in range(0, len(pairs), 2)) + bytes(4)
    with open(out, "w") as f:
        f.write("; made by tools/resgen.py\n        AREA    |C$$code|, CODE, READONLY\n")
        f.write("        EXPORT  %s\n%s\n        ADR     r0, block\n        MOV     pc, lr\nblock\n" % (func, func))
        for i in range(0, len(block), 16):
            f.write("        DCD     " + ", ".join("&%08X" % int.from_bytes(block[j:j + 4], "little")
                                              for j in range(i, min(i + 16, len(block)), 4)) + "\n")
        f.write("        END\n")


if __name__ == "__main__":
    main()
