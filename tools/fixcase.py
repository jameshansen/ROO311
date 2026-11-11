#!/usr/bin/env python3
"""Make GET/LNK/BIN file names in the assembler sources match the case of the files on disc.

    python tools/fixcase.py [--check]

RISC OS filing systems ignore case, so the sources name files however the author typed them
(GET s.vdu.VduDriver for s/vdu/vdudriver). A Linux build needs the names to match. Only the
parts of a name that resolve are touched: anything holding $variables or <variables> is left.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "Sources"
DIRECTIVE = re.compile(r'(^[ \t]+|")(GET|LNK|BIN|INCLUDE|INCBIN)([ \t]+)([A-Za-z0-9_:.\-!+]+)', re.M)


def children(d, cache={}):
    if d not in cache:
        cache[d] = {p.name.lower(): p for p in d.iterdir()} if d.is_dir() else {}
    return cache[d]


def resolve(base, parts):
    """Real spelling of parts under base, or None."""
    out, d = [], base
    for part in parts:
        hit = children(d).get(part.lower())
        if hit is None:
            return None
        out.append(hit.name)
        d = hit
    return out


def main():
    check = "--check" in sys.argv
    hdrs = [d for d in ROOT.rglob("*") if d.is_dir() and d.name.lower() == "hdr"]
    changed = unresolved = 0
    for f in sorted(p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts):
        try:
            text = f.read_bytes().decode("latin-1")
        except OSError:
            continue
        if "\0" in text[:4096] or not DIRECTIVE.search(text):
            continue

        def fix(m):
            nonlocal unresolved
            name = m.group(4)
            if name.lower().startswith("hdr:"):
                parts, bases, prefix = name[4:].split("."), hdrs, name[:4]
            elif ":" in name:
                return m.group(0)
            else:
                parts, bases, prefix = name.split("."), [a for a in f.parents if ROOT in a.parents or a == ROOT], ""
            for b in bases:
                real = resolve(b, parts)
                if real:
                    return m.group(1) + m.group(2) + m.group(3) + prefix + ".".join(real)
            unresolved += 1
            if check:
                print(f"unresolved: {f.relative_to(ROOT)}: {name}")
            return m.group(0)

        new = DIRECTIVE.sub(fix, text)
        if new != text:
            changed += 1
            if check:
                print(f"would fix: {f.relative_to(ROOT)}")
            else:
                f.write_bytes(new.encode("latin-1"))
    print(f"{changed} files {'need fixing' if check else 'fixed'}, {unresolved} names left alone")


if __name__ == "__main__":
    main()
