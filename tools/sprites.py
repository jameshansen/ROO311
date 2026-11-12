#!/usr/bin/env python3
"""Make a sprite file from another: leave sprites out, and take sprites from other files.

    python3 tools/sprites.py <in> <out> [--drop name ...] [--take file name[=newname] ...]

A sprite taken under a name the file already has replaces that sprite, in its place.
The ROM's Wimp sprite file is made with this (tools/prepare.py).
"""
import struct
import sys


def read(path):
    """The sprites of a file, in order, as (name, bytes)."""
    d = open(path, "rb").read()
    count, first = struct.unpack_from("<II", d, 0)
    o, out = first - 4, []                  # a file is a sprite area without its first word
    for _ in range(count):
        size, = struct.unpack_from("<I", d, o)
        out.append((d[o + 4:o + 16].split(b"\0")[0].decode("latin-1"), d[o:o + size]))
        o += size
    return out


def renamed(sprite, name):
    return sprite[:4] + name.encode("latin-1").ljust(12, b"\0") + sprite[16:]


def write(path, sprites):
    body = b"".join(s for _, s in sprites)
    open(path, "wb").write(struct.pack("<III", len(sprites), 16, 16 + len(body)) + body)


def build(src, drop=(), take=()):
    sprites = [(n, s) for n, s in read(src) if n not in drop]
    for path, name, new in take:
        s = renamed(dict(read(path))[name], new)
        names = [n for n, _ in sprites]
        if new in names:
            sprites[names.index(new)] = (new, s)
        else:
            sprites.append((new, s))
    return sprites


def main():
    src, out, *rest = sys.argv[1:]
    drop, take, mode = [], [], None
    while rest:
        a = rest.pop(0)
        if a in ("--drop", "--take"):
            mode = a
        elif mode == "--drop":
            drop.append(a)
        else:
            name, _, new = rest.pop(0).partition("=")
            take.append((a, name, new or name))
    write(out, build(src, drop, take))


if __name__ == "__main__":
    main()
