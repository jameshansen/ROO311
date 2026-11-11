#!/usr/bin/env python3
"""List a tokenised BBC BASIC V program (a RISC OS ",ffb" file) as text.

    python3 tools/basic.py <file,ffb>

The sources hold their build helpers and some applications in this form.
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


def main():
    d = open(sys.argv[1], "rb").read()
    for n, b in lines(d):
        print(f"{n:5d} {text(b)}")


if __name__ == "__main__":
    main()
