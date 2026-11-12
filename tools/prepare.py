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


def swi_numbers(comp):
    """The SWI names and numbers Squish puts in place of the names in SYS statements. It reads the C library's
    swis.h (FNn), which is what an assembly of RISC_OSLib's s.makehswis puts out."""
    with tempfile.TemporaryDirectory() as t:
        obj = Path(t) / "swis.o"
        subprocess.run([os.environ.get("ASASM", "asasm"), "-ABSolute", "-Uppercase", "-NOWarn", "-o", str(obj), "s/makehswis"],
                       cwd=comp.parents[1] / "Lib" / "RISC_OSLib", check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["arm-none-eabi-objcopy", "-O", "binary", str(obj), str(obj) + ".h"], check=True)
        text = Path(str(obj) + ".h").read_bytes().replace(b"\0", b"").decode("latin-1")
    swis = {}
    for line in text.splitlines():
        f = line.split()
        if len(f) >= 3 and f[0] == "#define" and not f[1].startswith("X") and f[1].find("_") >= 1:
            try:
                swis[f[1]] = int(f[2], 0)
            except ValueError:
                pass
    assert swis.get("Wimp_PollIdle") == 0x400E1, "swis.h did not come out as expected"
    return swis


def basic_app(runlink, version_tag=None):
    """A desktop application written in BASIC and held in the ROM as a module: the program goes into the
    module as a ResourceFS file and a short !RunLink program runs it in place. The original build made both
    small with BASIC's CRUNCH -1 (crunch.!RunImage) and then the Squish tool, which basic.crunch and
    basic.squish do here; Squish names the file it writes in the program's first line. Some take their
    module version from a tag in their Messages file (awk.Version)."""
    def make(comp):
        import basic
        swis = swi_numbers(comp)
        for src, dst in (("!RunImage,ffb", "Resources/!RunImage,ffb"), ("!RunLink,ffb", runlink)):
            name = dst.split(",")[0].replace("/", ".").encode()
            (comp / dst).write_bytes(basic.squish(basic.crunch((comp / "bas" / src).read_bytes()), name, swis))
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


def wimp(comp):
    """Resources.UK.ROM.Sprites: the ROM's one set of icons. It is the high resolution set without the window
    tiles for 256 and 32 thousand colour modes (100K; the 16 colour tile serves every mode), and with the task
    bar icon of the current RISC OS Open sources: the cog their Task Manager puts on the icon bar, which is
    "taskmanager" in their Window Manager's Sovereign sprites (Desktop/Wimp5). This Task Manager asks for
    "switcher", so the cog goes in under that name."""
    import sprites
    uk = comp / "Resources" / "UK"
    (uk / "ROM").mkdir(exist_ok=True)
    cog = comp.parent / "Wimp5" / "Resources" / "UK" / "Sovereign" / "Sprites,ff9"
    sprites.write(uk / "ROM" / "Sprites,ff9",
                  sprites.build(uk / "Sprites22,ff9", drop=("tile_1-16", "tile_1-8"), take=[(cog, "taskmanager", "switcher")]))


def desktop5(comp):
    """The resources of the current Desktop module, as its Makefile's shared rules make them.
    Resources.UK.ROM.Messages: Messages with the command help (CmdHelp) on the end.
    Resources.UK.ROM.Sprites: the banner sprites squashed, which is how the module wants them: a Squash
    file is "SQSH", the length, load and exec addresses of the original, a zero word, then the data.
    Resources.UK.ROM.Templates: the banner's template with its "RISC OS 5" reading "RISC OS", since this
    is not RISC OS 5."""
    import struct
    uk = comp / "Resources" / "UK"
    (uk / "ROM").mkdir(exist_ok=True)
    (uk / "ROM" / "Messages").write_bytes((uk / "Messages").read_bytes() + (uk / "CmdHelp").read_bytes())
    banner = (uk / "Sovereign" / "Sprites,ff9").read_bytes()
    (uk / "ROM" / "Sprites,fca").write_bytes(b"SQSH" + struct.pack("<IIII", len(banner), 0xFFFFF900, 0, 0) + compress(banner))
    template = (uk / "Templates,fec").read_bytes()
    assert template.count(b"RISC OS 5") == 1
    (uk / "ROM" / "Templates,fec").write_bytes(template.replace(b"RISC OS 5", b"RISC OS" + bytes(2)))


GENERATORS = {"Internat/Territory/TerritoryManager": territory, "Video/Render/Super": supersample,
              "Internat/Inter": international, "Video/Render/Fonts/ROMFonts": romfonts,
              "Desktop/Wimp": wimp,
              "Desktop/Desktop5": desktop5,
              "Apps/Chars": basic_app("Resources/UK/!RunLink,ffb"),
              "Apps/Help": basic_app("Resources/UK/ROM/!RunLink,ffb", "HelpID"),
              "Apps/EditApp": c_app("Edit", "EditId"), "Apps/Draw": c_app("Draw", "DrawID"),
              "Apps/Paint": c_app("Paint", "PntID"),
              "SystemRes/Configure": c_app("Configure", "VER")}


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
