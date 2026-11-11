/* The layout of a C application that uses the SharedCLibrary through its stubs: a plain image to load
 * and run at &8000. The stubs' code goes first, since it starts with the entry point. Their branch table
 * (Stub$$Entries) is written to when the library fills it in, which is fine in an application.
 * The zero-initialised data is part of the file, so nothing has to clear it. */
SECTIONS
{
  . = 0x8000;
  "Image$$RO$$Base" = .;
  .text : {
    *("Stub$$Code")
    *("Stub$$Entries")
    "C$$code$$Base" = .;
    *("C$$code")
    *(.text .text.*)
    "C$$code$$Limit" = .;
    *(.rodata .rodata.*)
    . = ALIGN(4);
    "RTSK$$Data$$Base" = .;
    *("RTSK$$Data")
    "RTSK$$Data$$Limit" = .;
  }
  "Image$$RW$$Base" = .;
  .data : {
    *(.data .data.*)
    "Image$$ZI$$Base" = .;
    *(.bss .bss.* COMMON)
    *("Stub$$Data")
    . = ALIGN(4);
    LONG(0)
  }
  "Image$$RW$$Limit" = .;

  /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) }
}
