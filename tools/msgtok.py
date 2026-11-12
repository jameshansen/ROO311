#!/usr/bin/env python3
"""Tokenise the ROM's message files the way the original ROM build did, to save space.

A messages file marks the messages that may be tokenised with comment lines (TagExtract):
    #{DictTokens}       the messages that follow are command help and syntax. The kernel prints them
                        with OS_PrettyPrint, which expands ESC,n to entry n of the dictionary in
                        Resources:$.Resources.Kernel.Dictionary and ESC,0 to the command's name.
    #{Token0=text}      the text that ESC,0 stands for in the messages that follow.
    #{HelpTokens}       the messages that follow are interactive help. The Help application expands
                        \\c to the message Tc in its own messages file.
    #{Default}          the messages that follow are left alone.
The original tools are MsgTok2 (dictionary) and MsgTok (help) in the Messages module's Utils; the token
tables are the ones its Data folder holds. A file that has tokenised messages also loses its comment lines,
as it did under those tools.

    tokenise(files)     files: {resource name: (data, file type)} as tools/mkres.py gathers them
"""
from pathlib import Path

HELPTOKENS = Path(__file__).resolve().parents[1] / "Sources" / "Internat" / "Messages" / "Data" / "HelpTokens"
ESC = 27


def dictionary_tokens(d):
    """(number, text) for each dictionary entry, longest first. An entry is a length byte, the text, a zero;
    its text can hold ESC,n for another entry, which is expanded here since messages are matched as plain text."""
    entries, i = [], 0
    while i < len(d) and d[i]:
        entries.append(d[i + 1:i + d[i] - 1])
        i += d[i]

    def expand(b, depth=0):
        out, j = bytearray(), 0
        while j < len(b):
            if b[j] == ESC and j + 1 < len(b):
                assert 1 <= b[j + 1] <= len(entries) and depth < 16, "bad dictionary"
                out += expand(entries[b[j + 1] - 1], depth + 1)
                j += 2
            else:
                out.append(b[j])
                j += 1
        return bytes(out)

    tokens = [(n + 1, expand(e)) for n, e in enumerate(entries)]
    return sorted((t for t in tokens if len(t[1]) > 2), key=lambda t: -len(t[1]))


def help_tokens(text):
    """(character, text) for each "Tc:text" line of the help token file, longest first."""
    tokens = []
    for line in text.split(b"\n"):
        if line:
            assert line[:1] == b"T" and line[2:3] == b":", line
            tokens.append((line[1], line[3:]))
    return sorted((t for t in tokens if len(t[1]) > 2), key=lambda t: -len(t[1]))


def substitute(s, tokens, lead):
    """Replace each token's text in s with the two bytes lead, number. The second byte of a pair already
    in the message is never looked at as text (MsgTok: "if (s[ii] == lead) ii++")."""
    s = bytearray(s)
    for number, text in tokens:
        i = 0
        while i <= len(s) - len(text):
            if s[i:i + len(text)] == text:
                s[i:i + len(text)] = bytes((lead, number))
            if s[i] == lead:
                i += 1
            i += 1
    return bytes(s)


def tokenise_file(data, dict_tokens, htokens):
    out, state, token0, changed = [], None, b"", False
    for line in data.split(b"\n"):
        if line.startswith(b"#"):
            word = line[1:].lower()
            if word.startswith(b"{default}"):
                state = None
            elif word.startswith(b"{dicttokens}"):
                state, token0 = "dict", b""
            elif word.startswith(b"{helptokens}"):
                state = "help"
            elif word.startswith(b"{token0=") and state == "dict":
                token0 = line[9:line.index(b"}")]
            out.append(line)
            continue
        tag, colon, text = line.partition(b":")
        if state and colon:
            if state == "dict":
                tokens = ([(0, token0)] if token0 else []) + dict_tokens
                text = substitute(text, tokens, ESC)
            else:
                text = substitute(text, htokens, ord("\\"))
            changed = True
            line = tag + colon + text
        out.append(line)
    if changed:
        out = [l for l in out if not l.startswith(b"#")]
    return b"\n".join(out)


def tokenise(files):
    """Tokenise every text file gathered for the ROM, and give the Help application its token messages."""
    dict_tokens = dictionary_tokens(files["Resources.Kernel.Dictionary"][0])
    helptext = HELPTOKENS.read_bytes()
    htokens = help_tokens(helptext)
    saved = 0
    for name, (data, ftype) in list(files.items()):
        if ftype == 0xFFF and name != "Resources.Kernel.Dictionary":
            new = tokenise_file(data, dict_tokens, htokens)
            saved += len(data) - len(new)
            files[name] = (new, ftype)
    data, ftype = files["Resources.Help.Messages"]
    files["Resources.Help.Messages"] = (data + (b"" if data.endswith(b"\n") else b"\n") + helptext, ftype)
    return saved - len(helptext)


def demo():
    d = bytes((7,)) + b" the " + b"\0" + bytes((10,)) + b"Syntax: " + b"\0" + bytes((8,)) + b"file" + bytes((ESC, 1)) + b"\0" + b"\0"
    toks = dictionary_tokens(d)
    assert (3, b"file the ") in toks and toks[0][1] == b"file the "
    src = b"#{DictTokens}\n#{Token0=Cat}\nHCAT:*Cat lists the file the user wants\nSCAT:Syntax: *Cat\n#{Default}\nX:Syntax: \n#{HelpTokens}\nH1:Click SELECT to go\n"
    out = tokenise_file(src, toks, help_tokens(b"T0:SELECT to \n"))
    assert out == b"HCAT:*\x1b\x00 lists\x1b\x01\x1b\x03user wants\nSCAT:\x1b\x02*\x1b\x00\nX:Syntax: \nH1:Click \\0go\n", out
    print("msgtok ok")


if __name__ == "__main__":
    demo()
