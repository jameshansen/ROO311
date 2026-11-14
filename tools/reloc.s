; Relocation for a C module loaded into the RMA, the part Acorn's linker added to a module (link -module).
; The C library's stubs call __RelocCode first thing when the module starts. It adds the distance between
; where the module is and where it was linked to every word the table lists, then records where it is, so
; a second start (*RMReInit) leaves it alone. tools/rmreloc.py appends the table to the linked module, a
; list of offsets from __RelocCode ending with -1, and fills in RelocWhere and RelocTable.

        AREA    |C$$code|, CODE, READONLY

        EXPORT  |__RelocCode|
        EXPORT  RelocWhere
        EXPORT  RelocTable

|__RelocCode|
        STMFD   sp!, {r0-r3, lr}
        ADR     r0, |__RelocCode|
        LDR     r1, RelocWhere
        SUBS    r1, r0, r1              ; how far it has moved
        LDMEQFD sp!, {r0-r3, pc}
        STR     r0, RelocWhere
        LDR     r2, RelocTable
        ADD     r2, r0, r2
10      LDR     r3, [r2], #4
        CMN     r3, #1
        LDMEQFD sp!, {r0-r3, pc}
        LDR     lr, [r0, r3]
        ADD     lr, lr, r1
        STR     lr, [r0, r3]
        B       %BT10

RelocWhere
        DCD     0                       ; the address __RelocCode was linked at, then where it is
RelocTable
        DCD     0                       ; the table's offset from __RelocCode

        END
