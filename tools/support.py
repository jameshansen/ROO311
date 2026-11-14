#!/usr/bin/env python3
"""ROO311's support pack: modules RISC OS 3.11 didn't have, for the programs that need them.

    python3 tools/support.py

Run by `sh build.sh support`, after a ROM build (it uses the C library's headers and stubs that
leaves in build/<machine>/clib). The sources are in Support/, and Support/UPSTREAM records where
each came from. It writes build/support/pack:

    extrom/WindowManager      Window Manager 4.01, the nested one, for an extension ROM: the Window
                              Manager can't be replaced once the desktop has started, and an
                              extension ROM's newer module takes the place of the ROM's at power on
    !System/Modules/...       CallASWI and the Toolbox modules, which a program's !Run loads itself
    !System, !Scrap           the two applications that set System$Path and Wimp$ScrapDir

The Toolbox modules are C. Acorn's linker made a module that runs wherever it is loaded (link
-module); here each is linked twice and tools/rmreloc.py turns the difference into the relocation
table tools/reloc.s works through when the module starts. Their Messages and Res files go into the
module as ResourceFS blocks, as Acorn's resgen made them (tools/resgen.py). Each is built from its
own Makefile's list of objects for a RAM build, compiled as the Makefile compiles them.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MACHINE = os.environ.get("MACHINE", "A5000")
B = ROOT / "build" / MACHINE
S = ROOT / "build" / "support"
SUP = ROOT / "Support"
GCC = os.environ.get("GCC", "arm-unknown-riscos-gcc")
ASASM = os.environ.get("ASASM", "asasm")
LOCALE = os.environ.get("LOCALE", "UK")
CMUNGE = str(Path(shutil.which(GCC)).parent / "cmunge")
LD = subprocess.run([GCC, "-print-prog-name=ld"], capture_output=True, text=True).stdout.strip()
LIBGCC = subprocess.run([GCC, "-mmodule", "-print-libgcc-file-name"], capture_output=True, text=True).stdout.strip()
HDR = S / "Hdr"

# The Toolbox modules, by folder, and the name each has in !System.Modules.Toolbox
TOOLBOX = [("Toolbox", "Toolbox"), ("Window", "Window"), ("Menu", "Menu"), ("IconBar", "Iconbar"),
           ("ProgInfo", "ProgInfo"), ("SaveAs", "SaveAs"), ("Scale", "Scale"), ("DCS", "DCS_Quit")]

# What toolchain/README.md calls C_DIALECT, and the rest of build.sh's modcc
C_FLAGS = ["-mmodule", "-ffixed-sl", "-mno-poke-function-name", "-fno-section-anchors", "-ffreestanding",
           "-fno-common", "-Os", "-nostdinc", "-funsigned-bitfields", "-fno-strict-aliasing", "-fwrapv",
           "-fno-delete-null-pointer-checks", "-D__arm", "-D___type="]


def run(args, cwd=None, env=None):
    r = subprocess.run([str(a) for a in args], cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode:
        sys.stdout.write(r.stdout + r.stderr)
        raise SystemExit("failed: " + " ".join(str(a) for a in args))
    return r.stdout


def cc(src, out, incs, defs):
    """One C source compiled to run inside a module, as build.sh's modcc 536 compiles it."""
    asm = out.with_suffix(".s")
    run([GCC] + C_FLAGS + defs + ["-I%s" % i for i in incs] + ["-x", "c", "-S", "-o", asm, src])
    text = re.sub(r"\(GOTOFF\)$", "", asm.read_text(), flags=re.M)
    asm.write_text(text)
    run([GCC, "-mmodule", "-c", "-o", out, asm])


def asm(src, out, cwd, extra=()):
    env = dict(os.environ, HDR_PATH=str(HDR), MACHINE=MACHINE, LOCALE=LOCALE)
    run([ASASM, "-Uppercase", "-NOWarn", "-G", "-apcs", "3/26bit"] + list(extra) + ["-o", out, src], cwd=cwd, env=env)


def headers():
    """The header set the support sources assemble against: ROO311's own (build/Hdr), with the Window
    Manager 4.01's headers over it, and what is still missing from the newer set (build/Hdr5)."""
    if HDR.exists():
        shutil.rmtree(HDR)
    shutil.copytree(ROOT / "build" / "Hdr", HDR, symlinks=True)
    for f in (SUP / "Desktop" / "Wimp" / "hdr").iterdir():
        shutil.copy(f, HDR / f.name)
    for f in (ROOT / "build" / "Hdr5").rglob("*"):
        t = HDR / f.relative_to(ROOT / "build" / "Hdr5")
        if f.is_dir():
            t.mkdir(exist_ok=True)
        elif not t.exists():
            shutil.copy(f, t)


def makefile_objs(comp):
    """The objects of a component's RAM build, and its resgen steps, from its Makefile."""
    mk = (comp / "Makefile").read_text("latin-1").replace("\\\n", " ")
    objs = re.search(r"^RAM_OBJS\s*=(.*)$", mk, re.M).group(1).split()
    objs = [o[2:] for o in objs if o.startswith("o.")]
    ram = dict(re.findall(r"^o\.(\w+):\s*(\w+)\.c", mk, re.M))       # o.mainRAM: main.c
    res = re.findall(r"^\s*resgen\s+(\w+)\s+\S+\s+(\S+)\s+(\S+)", mk, re.M)
    return objs, ram, res


def cmhg_text(hdr, comp, o):
    """A module header description with its #include "VersionNum" done, which cmhg -p had the C
    preprocessor do: the version and date macros put in where the description names them."""
    text = hdr.read_text("latin-1")
    defs = {}
    for name in re.findall(r'^#include\s+"([^"]+)"', text, re.M):
        for k, v in re.findall(r"^#define\s+(\w+)[ \t]*(.*)$", (comp / name).read_text("latin-1"), re.M):
            defs[k] = v.strip()
    text = re.sub(r"^#include.*$", "", text, flags=re.M)
    for k, v in defs.items():
        text = re.sub(r"\b%s\b" % k, v, text)
    out = o / "cmhg.txt"
    out.write_text(text, "latin-1")
    return out


def find_src(comp, kind, name):
    for d in (comp / kind, comp / "gadgets" / kind):
        for f in (d.iterdir() if d.is_dir() else []):
            if f.name.lower() == name.lower():
                return f
    return None


def library(name, comp, csrcs, ssrcs, incs):
    """An archive of module code, for the Toolbox modules to link with"""
    o = S / name
    if o.exists():
        shutil.rmtree(o)
    o.mkdir(parents=True)
    run([sys.executable, ROOT / "tools/incs.py", o / "inc", comp])
    objs = []
    for c in csrcs:
        cc(c, o / (c.name + ".o"), [o / "inc"] + incs + [B / "clib/inc"], [])
        objs.append(o / (c.name + ".o"))
    for s in ssrcs:
        asm(s, o / (s.name + ".o"), comp)
        objs.append(o / (s.name + ".o"))
    run([GCC[:-3] + "ar", "rcs", S / (name + ".a")] + objs)        # arm-unknown-riscos-ar beside the compiler


def toolbox_module(folder, name):
    comp = SUP / "Toolbox" / folder
    o = S / folder
    if o.exists():
        shutil.rmtree(o)
    o.mkdir(parents=True)
    objs, ram, res = makefile_objs(comp)
    tbox = SUP / "Toolbox" / "tboxlib"
    # tboxlib's headers include others of its own (objects.proginfo.h its os.h), then the module's own
    run([sys.executable, ROOT / "tools/incs.py", o / "inc", tbox])
    run([sys.executable, ROOT / "tools/incs.py", o / "inc", comp, tbox])
    incs = [o / "inc", comp, tbox, B / "clib/inc", S / "compat"]
    defs = ["-DUrsula"]
    out = []
    for obj in objs:
        f = o / (obj + ".o")
        hdr = find_src(comp, "cmhg", obj)
        if hdr:
            run([CMUNGE, "-tnorcroft", "-26bit", "-s", o / "hdr.s", "-d", o / "hdr.h", cmhg_text(hdr, comp, o)], cwd=comp)
            asm(o / "hdr.s", f, comp)
        elif obj in ram:                       # main.c built for RAM: without ROM, it registers its own resources
            cc(find_src(comp, "c", ram[obj]), f, incs, defs)
        elif find_src(comp, "c", obj):
            cc(find_src(comp, "c", obj), f, incs, defs + ["-DROM"])
        elif find_src(comp, "s", obj):
            asm(find_src(comp, "s", obj), f, comp)
        else:
            raise SystemExit("%s: no source for o.%s" % (folder, obj))
        out.append(f)
    for func, src, resname in res:
        src = src.replace("${LOCALE}", LOCALE).replace("LocalRes:", "Resources.%s." % LOCALE)
        path = next(p for p in (comp / src.replace(".", "/")).parent.iterdir()
                    if p.name.split(",")[0] == src.split(".")[-1])
        resname = resname.replace("${COMPONENT}", folder)
        run([sys.executable, ROOT / "tools/resgen.py", func, o / (func + ".s"), path, resname])
        asm(o / (func + ".s"), o / (func + ".o"), comp)
        out.append(o / (func + ".o"))
    libs = [S / "tboxlib.a", S / "wimplib.a", S / "stubs.o", S / "reloc.o", LIBGCC]
    for base in ("0", "0x10000"):
        run([LD, "-T", ROOT / "tools/romapp.ld", "--defsym", "ROMADDR=" + base, "-Map", o / ("link%s.map" % base),
             "-o", o / ("link%s.elf" % base)] + out + libs)
        run(["arm-none-eabi-objcopy", "-O", "binary", o / ("link%s.elf" % base), o / ("link%s" % base)])
    dest = S / "pack" / "!System" / "Modules" / "Toolbox" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(run([sys.executable, ROOT / "tools/rmreloc.py", o / "link0", o / "link0x10000", o / "link0.elf", dest]).strip())


def newer_module(src, cwd, out):
    """An assembler module in ObjAsm form from the current sources, which runs wherever it is. Like
    build.sh's newer, it assembles against the newer headers, for a 26-bit only machine."""
    o = S / (out.name + ".o")
    env = dict(os.environ, HDR_PATH=str(ROOT / "build" / "Hdr5"), MACHINE="Archimedes", LOCALE=LOCALE)
    run([ASASM, "-NOWarn", "-G", "-apcs", "3/26bit", "-o", o, src], cwd=cwd, env=env)
    run(["arm-none-eabi-ld", "-Ttext=0", "-e", "0", "-o", o.with_suffix(".elf"), o])
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["arm-none-eabi-objcopy", "-O", "binary", o.with_suffix(".elf"), out])
    print("%s: %d bytes" % (out, out.stat().st_size))


def main():
    S.mkdir(parents=True, exist_ok=True)
    if (S / "pack").exists():
        shutil.rmtree(S / "pack")
    headers()
    # <strings.h>, which Acorn's C tools of the time took as <string.h>
    (S / "compat").mkdir(exist_ok=True)
    (S / "compat" / "strings.h").write_text("#include <string.h>\n")
    env =dict(os.environ, HDR_PATH=str(HDR), MACHINE=MACHINE, SYSTEM="RO310", IMAGESIZE="2048K", LOCALE=LOCALE)
    o = S / "WindowManager.o"
    run([ASASM, "-ABSolute", "-Uppercase", "-NOWarn", "-G", "-o", o, "s/Wimp"], cwd=SUP / "Desktop" / "Wimp", env=env)
    run(["arm-none-eabi-ld", "-Ttext=0", "-e", "0", "-o", o.with_suffix(".elf"), o])
    (S / "pack" / "extrom").mkdir(parents=True)
    run(["arm-none-eabi-objcopy", "-O", "binary", o.with_suffix(".elf"), S / "pack" / "extrom" / "WindowManager"])
    print("WindowManager: %d bytes" % (S / "pack" / "extrom" / "WindowManager").stat().st_size)
    newer_module("s/CallASWI", SUP / "Utilities" / "CallASWI", S / "pack" / "!System" / "Modules" / "CallASWI")

    # the C library's stubs, as a module loaded into the RMA links with them, and the relocation code
    asm("clib/s/cl_stub_r", S / "stubs.o", ROOT / "Sources/Lib/RISC_OSLib")
    asm(ROOT / "tools/reloc.s", S / "reloc.o", ROOT)
    tbox = SUP / "Toolbox" / "tboxlib"
    library("tboxlib", tbox, [tbox / "c" / n for n in ("mem", "messages", "string32", "rmensure", "objsupport", "slist")],
            [tbox / "s" / "toolboxmem"], [tbox])         # its Makefile's tboxlibm, without debuglib's debug
    wimp = SUP / "Toolbox" / "ToolboxLib" / "wimplib"
    library("wimplib", wimp, [], sorted((wimp / "s").iterdir()), [])
    for folder, name in TOOLBOX:
        toolbox_module(folder, name)

    # !System and !Scrap: an Obey file each that sets the variable, as RISC OS 3's did
    for app, lines in (("!System", ["Set System$Dir <Obey$Dir>", "Set System$Path <System$Dir>."]),
                       ("!Scrap", ["Set Wimp$ScrapDir <Obey$Dir>.ScrapDir", "CDir <Wimp$ScrapDir>"])):
        d = S / "pack" / app
        d.mkdir(parents=True, exist_ok=True)
        for f in ("!Boot", "!Run"):
            (d / f).write_text("| %s %s, from ROO311's support pack\n" % (app, f) + "\n".join(lines) + "\n")
    shutil.copy(ROOT / "tools" / "support-readme.txt", S / "pack" / "!System" / "!Help")      # what the pack is
    pack_zip(S / "pack", S / "toolbox.zip")


def pack_zip(pack, out):
    """The pack as a zip, each file's type after a comma at the end of its name, which is how HostFS
    names a file on the computer and what SparkFS and Info-ZIP understand. The dates are fixed, so the
    zip is the same at every build."""
    import zipfile
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pack.rglob("*")):
            rel = f.relative_to(pack).as_posix()
            if f.is_dir():
                z.writestr(zipfile.ZipInfo(rel + "/", (2000, 1, 1, 0, 0, 0)), b"")
                continue
            if f.name in ("!Boot", "!Run"):
                rel += ",feb"                   # Obey
            elif "Modules" in f.parts or f.parent.name == "extrom":
                rel += ",ffa"                   # Module
            info = zipfile.ZipInfo(rel, (2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())
    print("%s: %d bytes" % (out, out.stat().st_size))


if __name__ == "__main__":
    main()
