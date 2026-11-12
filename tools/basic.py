#!/usr/bin/env python3
"""List a tokenised BBC BASIC V program (a RISC OS ",ffb" file) as text.

    python3 tools/basic.py <file,ffb>
    python3 tools/basic.py                  check crunch() against a small program

The sources hold their build helpers and some applications in this form. crunch() is BASIC's own CRUNCH
command, which the original build ran over the applications that go into the ROM.
"""
import sys

T = """OTHERWISE AND DIV EOR MOD OR ERROR LINE OFF STEP SPC TAB( ELSE THEN . OPENIN PTR PAGE TIME LOMEM HIMEM ABS ACS
ADVAL ASC ASN ATN BGET COS COUNT DEG ERL ERR EVAL EXP EXT FALSE FN GET INKEY INSTR( INT LEN LN LOG NOT OPENUP OPENOUT
PI POINT( POS RAD RND SGN SIN SQR TAN TO TRUE USR VAL VPOS CHR$ GET$ INKEY$ LEFT$( MID$( RIGHT$( STR$ STRING$( EOF
. . . WHEN OF ENDCASE ELSE ENDIF ENDWHILE PTR PAGE TIME LOMEM HIMEM SOUND BPUT CALL CHAIN CLEAR CLOSE CLG CLS DATA DEF
DIM DRAW END ENDPROC ENVELOPE FOR GOSUB GOTO GCOL IF INPUT LET LOCAL MODE MOVE NEXT ON VDU PLOT PRINT PROC READ REM
REPEAT REPORT RESTORE RETURN RUN STOP COLOUR TRACE UNTIL WIDTH OSCLI""".split()
TOKENS = {0x7F + i: t for i, t in enumerate(T)}
TWO = {0xC6: "SUM BEAT".split(),
       0xC7: "APPEND AUTO CRUNCH DELETE EDIT HELP LIST LOAD LVAR NEW OLD RENUMBER SAVE TEXTLOAD TEXTSAVE TWIN TWINO INSTALL".split(),
       0xC8: "CASE CIRCLE FILL ORIGIN POINT RECTANGLE SWAP WHILE WAIT MOUSE QUIT SYS INSTALL LIBRARY TINT ELLIPSE BEATS TEMPO VOICES VOICE STEREO OVERLAY".split()}


def lines(d):
    p = 0
    while p + 4 <= len(d) and d[p] == 0x0D and d[p + 1] != 0xFF:
        n, ln = d[p + 1] << 8 | d[p + 2], d[p + 3]
        yield n, d[p + 4:p + ln]
        p += ln


def text(b):
    out, i, quote, rem = [], 0, False, False
    while i < len(b):
        c = b[i]
        i += 1
        if c == 0x22:
            quote = not quote
        if quote or rem or c < 0x7F:
            out.append(chr(c))
        elif c == 0x8D:                             # an encoded line number
            x, y, z = b[i], b[i + 1], b[i + 2]
            i += 3
            x ^= 0x54
            out.append(str(((x & 0x30) << 2 ^ (y & 0x3F)) | (((x & 0x0C) << 12) ^ ((z & 0x3F) << 8))))
        elif c in TWO:
            out.append(TWO[c][b[i] - 0x8E] if b[i] - 0x8E < len(TWO[c]) else "?")
            i += 1
        else:
            out.append(TOKENS.get(c, "?"))
            rem = c in (0xF4, 0xDC)                 # REM and DATA run to the end of the line untokenised
    return "".join(out)


AND, EOR, ELSE, THEN, RND, DATA, REM = 0x80, 0x82, 0x8B, 0x8C, 0xB3, 0xDC, 0xF4
NAME = set(b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_`abcdefghijklmnopqrstuvwxyz")    # the zero entries of BASIC's LVTABLE


def keep_space(prev, c):
    """Whether a run of spaces between two items of a statement has to stay as one space (CRUNCHLOTS)."""
    if prev == c == 0x22:
        return True                                 # two quotes would read as a quote in a string
    if prev in (ord("$"), ord("%"), RND):
        return c in b"(!?"                          # an array, or an operator turned dyadic
    if prev in (EOR, AND):
        return c in NAME                            # the assembler reads EORS, ANDEQ
    if prev == ord(")") and c in b"!?":
        return True
    if prev in NAME or prev == ord("."):
        return c in NAME or c in b".$(!?"
    return False


def crunch_line(t, first):
    t += b"\r"
    out, i = bytearray(1), 0                        # the zero stands for the line's length byte, as in BASIC
    while True:                                     # one statement a turn
        while t[i] == 32:
            i += 1
        if t[i] in (ord("*"), DATA):
            return bytes(out[1:] + t[i:-1])         # a command or data runs to the end of the line as it is
        while True:
            c = t[i]
            if c == 32:
                while t[i] == 32:
                    i += 1
                c = t[i]
                if keep_space(out[-1], c):
                    out.append(32)
            if c == REM:
                if first:
                    return bytes(out[1:] + t[i:-1])
                c, i = 13, len(t) - 1
            if c == 0x22:
                j = t.find(b'"', i + 1)
                if j < 0:
                    return bytes(out[1:] + t[i:-1])
                out += t[i:j + 1]
                i = j + 1
                continue
            if c in (ord(":"), ELSE, THEN, 13):
                break
            out.append(c)
            i += 1
        if out[-1] == ord(":"):
            out.pop()                               # an empty statement
        if c == 13:
            return bytes(out[1:])
        out.append(c)
        i += 1


def crunch(d):
    """BASIC's CRUNCH -1 (CRUNCHROUTINE in the BASIC sources' Expr): the program without the spaces before and
    inside statements, its REMs (those of the first line stay), its empty statements and its empty lines."""
    out, first = bytearray(), True
    for n, t in lines(d):
        t = crunch_line(t, first)
        first = False
        if t:
            out += bytes((13, n >> 8, n & 255, len(t) + 4)) + t
    return bytes(out) + b"\r\xff"


IDENT = set(b"@abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_`0123456789")       # Squish's q$
SHORT = "@abcdefghijklmnopqrstuvwxyzABCDFGHIJKLMNOPQRSTUVWXZ_`0123456789"               # its g$: no E or Y
DIGITS = set(b"0123456789")
SUFFIX = {1: b"", 2: b"%", 3: b"$", 4: b"(", 12: b"%(", 13: b"$(", 5: b"", 6: b""}
BEFORE = (0x7F, 0xC9, 0xCB, 0xCC, 0xCD, 0xDD)       # OTHERWISE WHEN ENDCASE ELSE ENDIF DEF start a line
AFTER = (0xE7, 0xEF, 0xDC, 0xCA, 0xCB, 0xCD, 0xD7, 0xE1, 0xF7, 0xF9, 0xFA, 0xEE, 0xE0)     # IF, ENDPROC, END.. end one
BY = (b"\xdf", b"\xec", b"\xc8\x92", b"\xc8\x90")   # DRAW MOVE POINT FILL can take the word BY


def squish(d, name, swis={}):
    """The Squish tool of the RISC OS build (Library.Build.Squish 1.16, a BASIC program), which the original
    build ran over a crunched program: variables, procedures and functions get one and two letter names, the
    most used the shortest; lines are joined; hex numbers become decimal; a SWI name in a SYS statement
    becomes its number where swis has it; the first line is REM>name. Assembler and line number references
    are refused (Squish refuses the second too).

    Run under BASIC with the same swis.h, the real tool writes the same bytes for Chars, Help and their
    !RunLink programs. A name swis lacks stays a name here. The real tool then asks the OS for the number
    and loses the X of an X name, since BASIC reads its test U%=1<<17 as (U%=1)<<17."""
    src = [(n, t + b"\r") for n, t in lines(d)]

    def run(t, i, chars):                           # FNe: the character at i and those after it that are in chars
        i += 1
        while t[i] in chars:
            i += 1
        return i

    def number(t, i):
        j = run(t, i, DIGITS | {46})
        b = t[i:j]
        if t[j] == 69:                              # an exponent
            j += 1
            k = j + (t[j] in b"+-")
            if t[k] in DIGITS:
                b, j = b + b"E" + t[j:run(t, k, DIGITS)], run(t, k, DIGITS)
            else:
                j = k
        return 7, b, j

    def item(t, i, quote, start, by):
        """PROCm: the next item as (kind, text, index after it). Kinds: 0 token, 1 real, 2 integer, 3 string,
        4 12 13 their arrays, 5 PROC, 6 FN, 7 number, 8 end of line, 10 character, 11 the rest of the line."""
        if quote:
            return 10, t[i:i + 1], i + 1
        while t[i] == 32:
            i += 1
        n, end = t[i], len(t) - 1
        if i == end or n == REM or (n == 0xEF and t[i + 1] == 58):
            return 8, b"", end
        if n in (0x8D, 0xE4, 0xE5):
            raise ValueError("squish: line number reference")
        if n in (0xC6, 0xC7, 0xC8):
            return 0, t[i:i + 2], i + 2
        if n in (0xF2, 0xA4):
            j = run(t, i + 1, IDENT)
            return (5 if n == 0xF2 else 6), t[i + 1:j], j
        if n in b"&%":
            j = run(t, i, b"0123456789ABCDEFabcdef" if n == 38 else b"01")
            v = int(t[i + 1:j], 16 if n == 38 else 2)
            return 7, b"%d" % (v - (v >> 31 << 32)), j
        if n in DIGITS or (n == 46 and not start):
            return number(t, i)
        if n == 42:                                 # a star command if it starts a statement
            k = i - 1
            while k >= 0 and t[k] == 32:
                k -= 1
            if start or (k >= 0 and t[k] in (0xF5, 0x8C, 0x8B, 0xCC, 0x7F, 0x85, 0xEA)):
                return 11, t[i:end], end
        if n == DATA:
            return 11, t[i:end], end
        if by and t[i:i + 2] == b"BY":
            return 10, b"BY ", i + 2
        if n in IDENT:
            j = run(t, i, IDENT)
            kind, b = 1, t[i:j]
            if t[j] in b"%$":
                kind, j = 2 + (t[j] == 36), j + 1
            if t[j] == 40:
                kind, j = {1: 4, 2: 12, 3: 13}[kind], j + 1
            return kind, b, j
        return (0 if n > 126 else 10), t[i:i + 1], i + 1

    def items(t):
        """The items of a line as (kind, text, index after it, whether a string is open after it)."""
        i, quote, start, by, kind = 0, False, True, False, 0
        while i < len(t) - 1 and kind != 8:
            kind, b, i = item(t, i, quote, start, by)
            if kind == 10 and b == b'"':
                quote = not quote
            yield kind, b, i, quote
            start = False
            if not quote:
                by = by or (kind == 0 and b in BY)
                if kind == 10 and b == b"[":
                    raise ValueError("squish: assembler is not handled")
                if kind == 10 and b == b":":
                    start, by = True, False

    def allocate(count):
        """PROCf and PROCg: one letter names keep their names; the free letters go to the most used names, a
        letter each; the rest get two letters in the order they were met."""
        new = {n: n for n in count if len(n) == 1}
        count = {n: 0 if n in new else c for n, c in count.items()}
        for letter in SHORT[1:53].encode():
            if bytes((letter,)) in new:
                continue
            best = max(count, key=count.get, default=None)
            if best is None or not count[best]:
                break
            new[best], count[best] = bytes((letter,)), 0
        x = f = 1
        for n in count:
            if count[n]:
                a, x = SHORT[x] + SHORT[f], x + 1
                if SHORT[x] == "0":
                    x, f = 1, f + 1
                if a.upper() == "PC":
                    a, x = SHORT[x] + SHORT[f], x + 1
                new[n] = a.encode()
        return new

    names = {kind: {} for kind in SUFFIX}
    for _, t in src:
        for kind, b, _, _ in items(t):
            if kind in names:
                names[kind][b] = min(names[kind].get(b, 0) + 1, 255)
    new = {kind: allocate(count) for kind, count in names.items()}

    done, cur = [b"\xf4>" + name], bytearray()

    def newline():                                  # PROCk
        for c in b": :":
            while cur[-1:] == bytes((c,)):
                cur.pop()
        done.append(bytes(cur))
        cur.clear()

    for k, (_, t) in enumerate(src):
        stop = sys = False
        for nth, (kind, b, i, quote) in enumerate(items(t)):
            c = t[i:].lstrip(b" ")[0] if t[i] == 32 else 0          # what follows a space after the item
            if kind in (0, 11):
                if nth == 0 and cur and (kind == 11 or b[0] in BEFORE):
                    newline()
                cur += b
                sys = b == b"\xc8\x99"
                if b == bytes((RND,)) and t[i] not in b":;,'=/><(\"":
                    cur += b" "
                stop = stop or kind == 11 or b[0] in AFTER
            elif kind in names:
                cur += (b"\xf2" if kind == 5 else b"\xa4" if kind == 6 else b"") + new[kind][b] + SUFFIX[kind]
                if (kind in (1, 5, 6) and 31 < c < 127 and c not in b":;,'=/><\"") or (kind == 2 and c in b"(!?|$") \
                        or (kind == 3 and c == 40):
                    cur += b" "
                sys = False
            elif kind == 7:
                cur += b + (b" " if c and c in b"0123456789.E%&" else b"")
                sys = False
            elif kind == 10:
                if not sys:
                    cur += b
                elif b != b'"':
                    if quote:
                        swi += b
                    else:                           # not a name in quotes (Squish loses this character)
                        cur += b
                        sys = False
                elif quote:
                    swi = b""
                else:
                    n = swis.get(swi[swi[:1] == b"X":].decode("latin-1"))
                    cur += b'"' + swi + b'"' if n is None else b"%d" % (n | (swi[:1] == b"X") << 17)
                    sys = False
                if b == b'"' and not quote and c == 34:
                    cur += b" "
        if cur:
            while cur[-1:] == b" ":
                cur.pop()
            following = len(src[k + 1][1]) + 3 if k + 1 < len(src) else 0
            if not stop and len(cur) + 4 + following < 250:
                if cur[-1:] != b":":
                    cur += b":"
            else:
                newline()
    if cur:
        newline()
    assert max(map(len, done)) <= 248, "squish: line too long"
    return b"".join(bytes((13, n >> 8, n & 255, len(t) + 4)) + t for n, t in zip(range(5, 65280, 5), done)) + b"\r\xff"


def demo():
    assert [TOKENS[t] for t in (AND, EOR, ELSE, THEN, RND, DATA, REM)] == "AND EOR ELSE THEN RND DATA REM".split()

    def prog(*ls):
        return b"".join(bytes((13, 0, n + 1, len(t) + 4)) + t for n, t in enumerate(ls)) + b"\r\xff"
    src = prog(b"\xf4 > Demo", b"  a% = 1 : : \xf4 note", b"\xf4 gone", b"", b"\xf1 \"a b\" \"c\" ; x .5 : *cat  a",
               b"\xe7 a \x82 b \x8c x ! 4 = y (1) \x8b \xdc 1, 2", b"b$ = a$ + \"  : \xf4", b"z = a%!0 + \xb3 (1)")
    out = prog(b"\xf4 > Demo", b"a%=1", b"\xf1\"a b\" \"c\";x .5:*cat  a",
               b"\xe7a\x82 b\x8cx !4=y (1)\x8b\xdc 1, 2", b"b$=a$+\"  : \xf4", b"z=a%!0+\xb3 (1)")
    got = crunch(src)
    assert [t for _, t in lines(got)] == [t for _, t in lines(out)], [t for _, t in lines(got)]
    assert [n for n, _ in lines(got)] == [1, 2, 5, 6, 7, 8] and got.endswith(b"\r\xff")
    src = prog(b"\xf4 x", b"count%=0:total=1.5", b"\xf2show(count%)", b"\xe0", b"\xdd\xf2show(n%)",
               b"\xc8\x99\"XOS_Write0\",\"a b\" :\xf1n%;count%+&FF", b"\xe1")
    got = squish(src, b"T", {"OS_Write0": 2})
    assert list(lines(got)) == [(5, b"\xf4>T"), (10, b"a%=0:a=1.5:\xf2a(a%):\xe0"),
                                (15, b"\xdd\xf2a(n%):\xc8\x99131074,\"a b\":\xf1n%;a%+255:\xe1")], list(lines(got))
    print("basic ok")


def main():
    if len(sys.argv) < 2:
        return demo()
    d = open(sys.argv[1], "rb").read()
    for n, b in lines(d):
        print(f"{n:5d} {text(b)}")


if __name__ == "__main__":
    main()
