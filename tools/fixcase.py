#!/usr/bin/env python3
"""Make the assembler sources safe to build on Linux with AsAsm. Three fixes, all idempotent:

    python tools/fixcase.py [--check] [Support]

The sources under Sources/, or with Support those of the support pack, whose Hdr: names are looked for
in the headers of both.

1. GET/LNK/BIN file names match the case of the files on disc. RISC OS filing systems ignore case,
   so the sources name files however the author typed them (GET s.vdu.VduDriver for
   s/vdu/vdudriver). Only the parts of a name that resolve are touched: anything holding
   $variables or <variables> is left.
2. A line ending in a backslash gets a space after it. AsAsm reads a final backslash as a line
   continuation, as ObjAsm does, and swallows the next line; AAsm did not. The sources have
   comments that end that way ("; \\" beside the backslash's own font row).
3. A backslash character constant, "\\" or '\\', becomes &5C. AsAsm reads a backslash in a string as
   the start of a C escape sequence, so "\\" is a string with no end. Longer strings that hold a
   backslash are left for a hand edit ("abc", &5C, "def").
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "Sources"
ASM_DIRS = {"s", "hdr", "testsrc", "oldtestsrc"}
ASM_COMPONENTS = ("Programmer/BASIC",)          # components that keep their assembler sources in their top folder
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


def backslash_constant(line):
    """&5C for "\\" and '\\' in the code part of a line (not in its comment)."""
    if "\\" not in line:
        return line
    code, quote = len(line), False
    for i, ch in enumerate(line):
        if ch == '"':
            quote = not quote
        elif ch == ";" and not quote:
            code = i
            break
    head = line[:code].replace('"\\"', "&5C").replace("'\\'", "&5C")
    if "\\" in head and re.match(r"\S*\s+(DCB|=)\s", head):
        # a data directive: "ab\cd" becomes "ab", &5C, "cd"
        def split(m):
            parts = m.group(1).split("\\")
            out = []
            for i, part in enumerate(parts):
                if i:
                    out.append("&5C")
                if part:
                    out.append(f'"{part}"')
            return ", ".join(out)
        head = re.sub(r'"((?:[^"]|"")*)"', lambda m: split(m) if "\\" in m.group(1) else m.group(0), head)
    return head + line[code:]


def main():
    global ROOT
    check = "--check" in sys.argv
    sources = ROOT
    if "Support" in sys.argv:
        ROOT = ROOT.parent / "Support"
    hdrs = [d for r in {sources, ROOT} for d in r.rglob("*") if d.is_dir() and d.name.lower() == "hdr"]
    changed = unresolved = slashes = 0
    for f in sorted(p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts):
        try:
            text = f.read_bytes().decode("latin-1")
        except OSError:
            continue
        if "\0" in text[:4096]:
            continue
        if ASM_DIRS & {part.lower() for part in f.parts[:-1]} or f.parent.relative_to(ROOT).as_posix() in ASM_COMPONENTS:
            new = re.sub(r"\\(\r?)$", r"\\ \1", text, flags=re.M)
            new = "\n".join(backslash_constant(line) for line in new.split("\n"))
            if new != text:
                slashes += 1
                if check:
                    print(f"would fix backslashes: {f.relative_to(ROOT)}")
                else:
                    f.write_bytes(new.encode("latin-1"))
                    text = new
        if not DIRECTIVE.search(text):
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
    print(f"{changed} files {'need' if check else 'had'} file names fixed, {unresolved} names left alone, "
          f"{slashes} files {'need' if check else 'had'} backslashes fixed")


if __name__ == "__main__":
    main()
