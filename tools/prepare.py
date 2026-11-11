#!/usr/bin/env python3
"""Make the generated source files a component needs before it is assembled.

    python3 tools/prepare.py <component folder>

The original build made these with programs run under RISC OS (BASIC programs, the Squash module).
Each generator here is a port of the one named beside it, and writes the same file. The files are
build products and are not kept in git.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def compress(data):
    """Unix compress, 12 bits, as the Squash module writes and reads (c.cssr, c.zssr).

    Codes are packed low bit first and written in groups of eight; when the code width grows the rest of
    the group is padded out, which the decompressor relies on. The table is never cleared: once it is
    full the remaining data is coded with what is there.
    """
    out = bytearray(b"\x1f\x9d\x8c")
    table, free, bits, maxcode = {}, 257, 9, 511
    buf = acc = 0          # acc: bits held in buf; group: bits written in the current group of eight codes
    group = 0
    packed = bytearray()

    def put(code):
        nonlocal buf, acc, group, bits, maxcode
        buf |= code << acc
        acc += bits
        group += bits
        while acc >= 8:
            packed.append(buf & 0xFF)
            buf >>= 8
            acc -= 8
        if group == bits * 8:
            group = 0
        if free > maxcode and bits < 12:
            if group:                       # pad the group of eight codes out before changing width
                if acc:
                    packed.append(buf & 0xFF)
                    buf = acc = 0
                packed.extend(b"\0" * ((bits * 8 - group) // 8))
                group = 0
            bits += 1
            maxcode = 4096 if bits == 12 else (1 << bits) - 1

    if data:
        ent = data[0]
        for c in data[1:]:
            key = (ent, c)
            if key in table:
                ent = table[key]
                continue
            put(ent)
            if free < 4096:
                table[key] = free
                free += 1
            ent = c
        put(ent)
        if acc:
            packed.append(buf & 0xFF)
    return bytes(out + packed)


def territory(comp):
    """z.SystemDisc: the "insert system disc" sprite squashed (MakeSprite, which called Squash_Compress)."""
    (comp / "z").mkdir(exist_ok=True)
    (comp / "z" / "SystemDisc").write_bytes(compress((comp / "SystemDisc,ff9").read_bytes()))


def supersample(comp):
    """s.Matrix1 and s.Matrix2: the weighting tables (GenMatrix1, GenMatrix2)."""
    def weigh(x, w):
        return sum(k for b, k in enumerate(w) if x >> b & 1)

    def table(xs, w, row_start):
        """One DCB row per 16 values of x, a new row wherever x AND 15 = row_start."""
        return "".join(("\n        DCB     " if (x & 15) == row_start else ",") + f"&{weigh(x, w):02X}" for x in xs) + "\n"

    w1, w2, w3 = (1, 2, 3, 4, 3, 2, 1), (1, 2, 4, 6, 6, 6, 4, 2, 1), (1, 4, 8, 12, 13, 12, 8, 4, 1)
    m1 = "; > s.Matrix1\n\nLookupTable" + table(range(128), w1, 0) + "\n        END\n\n"
    m2 = ("; > s.Matrix2\n\n      [ Version >= 5\n" + table(range(511, 0, -1), w2, 15) +
          "\n     |\n\nLookupTable1" + table(range(512), w2, 0) + "\n     ]\n\n" +
          "LookupTable2" + table(range(512), w3, 0) + "\n        END\n\n")
    (comp / "s" / "Matrix1").write_text(m1)
    (comp / "s" / "Matrix2").write_text(m2)


def international(comp):
    """s.IntHelpTok: the command help. IntHelpSrc is an assembler source whose output is itself assembler
    source text, which the original build then tokenised. The same assembly is run here, untokenised."""
    with tempfile.TemporaryDirectory() as t:
        obj = Path(t) / "IntHelp.o"
        subprocess.run([os.environ.get("ASASM", "asasm"), "-ABSolute", "-Uppercase", "-NOWarn", "-o", str(obj), "IntHelpSrc"],
                       cwd=comp, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["arm-none-eabi-objcopy", "-O", "binary", str(obj), str(comp / "s" / "IntHelpTok")], check=True)


def romfonts(comp):
    """Fonts.Encodings.Base0: a copy of the file RISC OS calls "/Base0", under a name AsAsm can open."""
    enc = comp / "Fonts" / "Encodings"
    (enc / "Base0").write_bytes((enc / ".Base0").read_bytes())


def message_version(comp, tag):
    """The version and date an application keeps in its Messages file, as "<tag>:2.28 (18-Jan-95)"."""
    for line in (comp / "Resources" / "UK" / "Messages").read_text(encoding="latin-1").splitlines():
        t, _, rest = line.partition(":")
        if t == tag:
            version, date = rest.split()[:2]
            return (version, *date.strip("()").split("-"))
    raise SystemExit(f"{comp}: no {tag} in Messages")


def basic_app(runlink, version_tag=None):
    """A desktop application written in BASIC and held in the ROM as a module: the program goes into the
    module as a ResourceFS file and a short !RunLink program runs it in place. The original build crunched
    and squashed both (the "squish" tool) to save space; here they go in as they are. Some take their
    module version from a tag in their Messages file (awk.Version)."""
    def make(comp):
        (comp / "Resources" / "!RunImage,ffb").write_bytes((comp / "bas" / "!RunImage,ffb").read_bytes())
        (comp / runlink).write_bytes((comp / "bas" / "!RunLink,ffb").read_bytes())
        if version_tag:
            version, d, m, y = message_version(comp, version_tag)
            lines = ["; > Version - generated from Messages, used by s.Main", "",
                     "        GBLS    VString", "        GBLS    Date", "",
                     f'VString SETS    "{version}"', f'Date    SETS    "{d} {m} 19{y}"', "",
                     "        END", ""]
            (comp / "s" / "Version").write_text("\n".join(lines))
    return make


def c_app(name, version_tag):
    """A desktop application written in C and held in the ROM as a module, with RISC_OSLib's module wrapper
    as its header. The wrapper takes the name and version from s.AppName (awk.AppName) and the files it
    registers with ResourceFS from s.ResFiles, which Draw and Paint keep as asm.ResFiles."""
    def make(comp):
        (comp / "s").mkdir(exist_ok=True)
        if (comp / "asm" / "ResFiles").exists():
            (comp / "s" / "ResFiles").write_bytes((comp / "asm" / "ResFiles").read_bytes())
        version, d, m, y = message_version(comp, version_tag)
        lines = ["; AppName - generated from Messages, used by ModuleWrap", "",
                 "                   GBLS    ApplicationName", "                   GBLS    ApplicationVersion", "",
                 f'ApplicationName    SETS    "{name}"', f'ApplicationVersion SETS    "{version} ({d} {m} 19{y})"', "",
                 "                   END", ""]
        (comp / "s" / "AppName").write_text("\n".join(lines))
    return make


GENERATORS = {"Internat/Territory/TerritoryManager": territory, "Video/Render/Super": supersample,
              "Internat/Inter": international, "Video/Render/Fonts/ROMFonts": romfonts,
              "Apps/Chars": basic_app("Resources/UK/!RunLink,ffb"),
              "Apps/Help": basic_app("Resources/UK/ROM/!RunLink,ffb", "HelpID"),
              "Apps/EditApp": c_app("Edit", "EditId"), "Apps/Draw": c_app("Draw", "DrawID"),
              "Apps/Paint": c_app("Paint", "PntID")}


def main():
    comp = Path(sys.argv[1])
    for suffix, fn in GENERATORS.items():
        if comp.as_posix().endswith(suffix):
            fn(comp)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--compress":      # compress <in> <out>, for checking against gzip -d
        Path(sys.argv[3]).write_bytes(compress(Path(sys.argv[2]).read_bytes()))
    else:
        main()
