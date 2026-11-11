/* The layout of a C program held in the ROM as a module, linked to run where it sits.
 *
 *   ROMADDR  the address of the module in the ROM (--defsym, from build.sh)
 *
 * The module wrapper's header comes first, then the code, which runs in place, then the image of the
 * initialised statics. When the program starts the library copies that image to the module's workspace
 * and clears the rest: the zero-initialised statics and the room the stubs hold for the library's own.
 * Those take no space in the ROM. */
SECTIONS
{
  . = ROMADDR;
  "Image$$RO$$Base" = .;
  .text : {
    *("!!!Module$$Header")
    *("!Header$$code")       /* the name CMunge gives a generated header */
    *("Stub$$Code")
    *("Stub$$Entries")
    "C$$code$$Base" = .;
    *("C$$code")
    *("C$$Code")
    *(.text .text.*)
    INPUT_SECTION_FLAGS (SHF_EXECINSTR) *(*)     /* code areas with names of a module's own */
    "C$$code$$Limit" = .;
    *(.rodata .rodata.*)
    . = ALIGN(4);
    "RTSK$$Data$$Base" = .;
    *("RTSK$$Data")
    "RTSK$$Data$$Limit" = .;
  }
  "Image$$RO$$Limit" = .;
  "Image$$RW$$Base" = .;
  .data : {
    *("!!!asm$$Data")        /* Squash: the statics its header addresses, which have to come first */
    *(.data .data.*)
    . = ALIGN(4);
  }
  "Image$$ZI$$Base" = .;
  .bss (NOLOAD) : {
    *(.bss .bss.* COMMON)
    *("Stub$$Data")
    . = ALIGN(4);
  }
  "Image$$RW$$Limit" = .;
  "Image$$ZI$$Limit" = .;

  /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) }
}
