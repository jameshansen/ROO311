/* The layout of the SharedCLibrary module, linked to run where it sits in the ROM.
 *
 *   ROMADDR  the address of the module in the ROM
 *   CLSIZE   the size of the C library's static data, as every client's stubs reserve it
 *
 * Both come from build.sh (--defsym). The names with $$ in them are the ones Acorn's linker made for the
 * base and limit of an area; the assembler sources import them.
 */
SECTIONS
{
  . = ROMADDR;
  .text : {
    *("!!!Module$$Header")
    *("AA$$code")
    *("K$$Code")
    "C$$code$$Base" = .;
    *("C$$code")
    *(.text .text.*)
    "C$$code$$Limit" = .;
    *(.rodata .rodata.*)
    . = ALIGN(4);
    "Lib$$Init$$Base" = .;
    *("Lib$$Init")
    "Lib$$Init$$Limit" = .;
    "RTSK$$Data$$Base" = .;
    *("RTSK$$Data")
    "RTSK$$Data$$Limit" = .;
  }

  /* The static data: the kernel's, then the C library's, then RISC_OSLib's. The library copies each part
   * to a client, whose stubs hold a fixed amount of room for it, and refuses a client whose room is a
   * different size. So each part is made up to that size exactly. If the C sources' own statics outgrow
   * it the location counter would have to go backwards here, and the link fails.
   * build.sh puts the C library's compiled objects in a folder c and RISC_OSLib's in a folder r. */
  .data : {
    *k_mod_r.o("C$$data")
    cl_data = .;
    *cl_mod_r.o("C$$data")
    */c/*.o(.data .data.* .bss .bss.* COMMON)
    . = cl_data + CLSIZE;
    "CLib_data_end" = .;
    rl_data = .;
    *rl_mod_r.o("C$$data")
    */r/*.o(.data .data.* .bss .bss.* COMMON)
    . = rl_data + RLSIZE;
    "RLib_data_end" = .;
  }

  /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) }
}
