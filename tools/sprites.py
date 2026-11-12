#!/usr/bin/env python3
"""Make a sprite file from another: leave sprites out, and take sprites from other files.

    python3 tools/sprites.py <in> <out> [--drop name ...] [--take file name[=newname] ...]

A sprite taken under a name the file already has replaces that sprite, in its place. A sprite taken in the
newer sprite form is put into the older one, which the rest of the ROM's icons are in.
The ROM's Wimp sprite file is made with this (tools/prepare.py). With no arguments it checks itself.
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


def old_format(sprite, mode=20):
    """A 16 colour sprite of the newer form (a mode word that gives its type and resolution, and a mask of one
    bit a pixel) in the form RISC OS 3.11 knew: a mode number, and a mask the shape of the image. The ROM's
    icons are all of that form. A sprite already in it comes back as it is."""
    size, ww, h, fb, lb, img, msk, word = struct.unpack_from("<I12x7I", sprite)
    if word < 256:
        return sprite
    new_16_colour_90dpi = word >> 27 == 3 and (word >> 1) & 0x1FFF == 90 and (word >> 14) & 0x1FFF == 90
    assert new_16_colour_90dpi and fb == 0 and img <= msk, "not a 16 colour sprite at 90 dots an inch"
    row, width = (ww + 1) * 4, ((ww + 1) * 32 - (31 - lb)) // 4
    image, mask = sprite[img:img + row * (h + 1)], b""
    if msk != img:
        mrow = (width + 31) // 32 * 4
        for y in range(h + 1):
            bits = int.from_bytes(sprite[msk + y * mrow:msk + (y + 1) * mrow], "little")
            mask += sum(15 << 4 * x for x in range(width) if bits >> x & 1).to_bytes(row, "little")
    head = struct.pack("<I12s7I", img + len(image) + len(mask), sprite[4:16], ww, h, fb, lb, img, img + (len(image) if mask else 0), mode)
    return head + sprite[44:img] + image + mask


def build(src, drop=(), take=()):
    sprites = [(n, s) for n, s in read(src) if n not in drop]
    for path, name, new in take:
        s = renamed(old_format(dict(read(path))[name]), new)
        names = [n for n, _ in sprites]
        if new in names:
            sprites[names.index(new)] = (new, s)
        else:
            sprites.append((new, s))
    return sprites


def demo():
    # 3 pixels by 2, 16 colours at 90 dots an inch, the mask's rows 101 and 010
    new = struct.pack("<I12s7I", 60, b"x", 0, 1, 0, 11, 44, 52, 3 << 27 | 90 << 14 | 90 << 1 | 1) + bytes.fromhex("21030000 54060000 05000000 02000000")
    old = old_format(new)
    assert struct.unpack_from("<I12x7I", old) == (60, 0, 1, 0, 11, 44, 52, 20) and old[44:] == bytes.fromhex("21030000 54060000 0f0f0000 f0000000")
    assert old_format(old) == old
    print("sprites ok")


def main():
    if len(sys.argv) < 3:
        return demo()
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
