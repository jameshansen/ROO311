#!/usr/bin/env python3
"""Line a built image up against a reference ROM and show where the code differs.

    python3 tools/romdiff.py build/A5000/Kernel ROM311              summary and list of differing hunks
    python3 tools/romdiff.py build/A5000/Kernel ROM311 --show 12    disassemble hunk 12, both sides
    python3 tools/romdiff.py build/A5000/Kernel ROM311 --at 0x3801234   our side of the hunk holding that address
    python3 tools/romdiff.py ... --len 0x25878      compare only this much of the reference (default: our length + 25%)
    python3 tools/romdiff.py ... --elf build/A5000/Kernel.elf   name the source line of each hunk (the ELF holds line
                                                    numbers when AsAsm is run with -G)

The two images are different builds, so every branch and PC-relative load differs in its offset. Words are
compared after masking those offsets out, then matched with difflib, so what is left is code that is really
different: inserted, deleted or changed instructions. Needs arm-none-eabi-objdump for --show.
"""
import argparse
import difflib
import struct
import subprocess
import tempfile

BASE = 0x03800000


def tokens(d):
    out = []
    for (w,) in struct.iter_unpack("<I", d[: len(d) & ~3]):
        top = (w >> 25) & 7
        if top == 5:                                            # B, BL
            w &= 0xFF000000
        elif (w >> 26) & 3 == 1 and (w >> 16) & 15 == 15 and not w & (1 << 25):   # LDR/STR [pc, #n]
            w &= 0xFF7FF000
        elif top == 1 and (w >> 16) & 15 == 15 and (w >> 21) & 15 in (2, 4) and not w & (1 << 20):   # ADR
            w = (w & 0xF000F000) | 0x028F0000
        elif BASE <= w < BASE + 0x800000:                       # a ROM address held as data
            w = BASE
        out.append(w)
    return out


def disasm(d, start, end, vma):
    if end <= start:
        return ""
    with tempfile.NamedTemporaryFile(suffix=".bin") as f:
        f.write(d[start:end])
        f.flush()
        r = subprocess.run(["arm-none-eabi-objdump", "-D", "-b", "binary", "-marm", "-Mreg-names-raw",
                            f"--adjust-vma={vma + start:#x}", f.name], capture_output=True, text=True)
    return "\n".join(line for line in r.stdout.splitlines() if line.startswith(" ") and ":\t" in line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ours")
    ap.add_argument("ref")
    ap.add_argument("--show", type=int, action="append", default=[])
    ap.add_argument("--at", type=lambda x: int(x, 0))
    ap.add_argument("--len", type=lambda x: int(x, 0))
    ap.add_argument("--context", type=int, default=6, help="matching instructions to show either side of a hunk")
    ap.add_argument("--min", type=int, default=1, help="list only hunks of at least this many words")
    ap.add_argument("--elf", help="our ELF with line numbers, to name the source line of each hunk")
    a = ap.parse_args()
    ours = open(a.ours, "rb").read()
    ref = open(a.ref, "rb").read()[: a.len or len(ours) * 5 // 4]
    ta, tb = tokens(ours), tokens(ref)
    ops = [o for o in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes()]
    same = sum(i2 - i1 for tag, i1, i2, j1, j2 in ops if tag == "equal")
    hunks = [o for o in ops if o[0] != "equal"]
    where = {}
    if a.elf:
        addrs = [f"{BASE + o[1] * 4:#x}" for o in hunks]
        r = subprocess.run(["arm-none-eabi-addr2line", "-e", a.elf] + addrs, capture_output=True, text=True)
        where = {o[1]: "/".join(line.split("/")[-2:]) for o, line in zip(hunks, r.stdout.splitlines())}
    print(f"ours {len(ta)} words, reference {len(tb)} words, {same} match ({100 * same / len(ta):.1f}% of ours), {len(hunks)} hunks")
    for n, (tag, i1, i2, j1, j2) in enumerate(hunks):
        if a.at is not None and BASE + i1 * 4 <= a.at <= BASE + max(i2, i1 + 1) * 4:
            a.show.append(n)
        if not a.show and max(i2 - i1, j2 - j1) >= a.min:
            print(f"{n:4d} {tag:8s} ours {BASE + i1 * 4:08x} +{i2 - i1:<5d} ref {BASE + j1 * 4:08x} +{j2 - j1:<5d} {where.get(i1, '')}")
    for n in a.show:
        tag, i1, i2, j1, j2 = hunks[n]
        c = a.context
        print(f"=== hunk {n} ({tag}): ours {BASE + i1 * 4:08x} +{i2 - i1} words, reference {BASE + j1 * 4:08x} +{j2 - j1} words  {where.get(i1, '')}")
        print("--- ours")
        print(disasm(ours, (i1 - c) * 4, (i2 + c) * 4, BASE))
        print("--- reference")
        print(disasm(ref, (j1 - c) * 4, (j2 + c) * 4, BASE))


if __name__ == "__main__":
    main()
