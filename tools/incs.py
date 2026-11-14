#!/usr/bin/env python3
"""Make the headers a component's C sources include findable under the names they use.

    python3 tools/incs.py <include folder> <component folder> <library folder>...

Norcroft read a name such as "objects.toolbox.h" or "h.mem" the RISC OS way: folders are separated by
dots and the h is a folder, so both mean a file in a folder named h. "^" is the folder above the
source's own, which for a source in gadgets/c is the component itself. Each name found in an #include
gets a link in the include folder to the file it means, looked for in the component, then in each
library folder in turn. A name nothing matches is left to the compiler's other include folders.
"""
import os
import re
import sys
from pathlib import Path


def candidates(name):
    """The paths, relative to a folder searched, that an include name can mean."""
    parts = name.split(".")
    if parts[0] == "^":
        parts = parts[1:]
    out = []
    if len(parts) >= 2 and parts[-1].lower() == "h":          # objects.toolbox.h, mem.h
        out.append(Path(*parts[:-2], "h", parts[-2]))
    if len(parts) >= 2 and parts[0].lower() == "h":           # h.mem, h.objects.toolbox
        out.append(Path("h", *parts[1:]))
    out.append(Path(*parts))
    return out


def find(folder, rel):
    """rel under folder, matching each part without regard to case, as RISC OS does."""
    at = folder
    for part in rel.parts:
        try:
            match = next((e for e in os.listdir(at) if e.lower() == part.lower()), None)
        except NotADirectoryError:
            return None
        if match is None:
            return None
        at = at / match
    return at if at.is_file() else None


def main():
    inc, comp, libs = Path(sys.argv[1]), Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]]
    inc.mkdir(parents=True, exist_ok=True)
    names = {}          # each name, and the folders of the sources that include it (gadgets for gadgets/c/x)
    for src in comp.rglob("*"):
        if src.is_file() and src.parent.name in ("c", "h"):
            for name in re.findall(r'#\s*include\s*["<]([^">]+)[">]', src.read_text("latin-1")):
                names.setdefault(name, set()).add(src.parent.parent)
    for name in sorted(names):
        for rel in candidates(name):
            where = sorted(names[name]) + [comp] + libs
            hit = next((h for d in where for h in [find(d, rel)] if h), None)
            if hit:
                link = inc / name
                if link.is_symlink() or link.exists():
                    link.unlink()
                link.symlink_to(hit.resolve())
                break


if __name__ == "__main__":
    main()
