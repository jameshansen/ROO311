#!/usr/bin/env python3
"""Make the help text source a component's Makefile would have made with the "tokenise" tool.

    python3 tools/tokhelp.py <component folder>

The Makefile rule looks like
    s.TokHelpSrc: Hdr:Tokens HelpSrc
            tokenise Hdr:Tokens HelpSrc $@
tokenise swaps common words for the kernel's dictionary tokens to save ROM space. The untokenised text
is valid as it stands, so the file is copied across unchanged. The copy is not kept in git.
"""
import re
import shutil
import sys
from pathlib import Path


def main():
    comp = Path(sys.argv[1])
    make = comp / "Makefile"
    if not make.exists():
        return
    lines = make.read_text(encoding="latin-1").splitlines()
    for i, line in enumerate(lines[:-1]):
        m = re.match(r"(\S+)\s*:", line)
        t = re.match(r"\s+\S*[Tt][Oo][Kk][Ee][Nn][Ii][Ss][Ee]\S*\s+\S+\s+(\S+)\s+\$@", lines[i + 1])
        if m and t:
            dst, src = (comp / x.replace(".", "/") for x in (m.group(1), t.group(1)))
            if src.exists() and (not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime):
                shutil.copyfile(src, dst)
                print(f"{dst}: copied from {src.name}")


if __name__ == "__main__":
    main()
