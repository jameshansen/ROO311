# The ROO26 toolchain

ROO26 builds with two open tools and nothing proprietary.

| Tool | Version | Used for |
|---|---|---|
| AsAsm | 2.01, GCCSDK svn r7800 | Every assembler source (the kernel and most modules) |
| GCC for RISC OS | 4.7.4, GCCSDK release 6, with binutils 2.24 | The C parts: SharedCLibrary, SpriteExtend, Filer_Action, the applications |

Plus `binutils-arm-none-eabi` (any recent version) for linking and Python 3 for the build scripts.

## Why GCC 4.7.4

It is the last GCC that can produce code for these machines.

- An ARM2 or ARM3 has the ARMv2 instruction set: no `MRS`/`MSR`, no long multiply, no halfword loads. GCC 9 removed every architecture before ARMv4.
- RISC OS floating point is FPA, through the FPEmulator module on a machine with no FPA chip. GCC 4.8 removed FPA.
- The SharedCLibrary expects the RISC OS procedure call standard: a frame pointer chain, a stack limit in `sl` checked on entry to each function, and floating point results in `f0`. GCCSDK's `-mlibscl` target generates that.

The RISC OS Open sources were written for the Norcroft C compiler from Acorn's DDE, which is not free. GCC stands in for it, and the changes that takes are made in the sources with `ROO26:` comments.

## What the compiler does by default

With `-mlibscl` (code that uses the SharedCLibrary) or `-mmodule` (code inside a module) the defaults are already the ones ROO26 needs. `arm-unknown-riscos-gcc -Q --help=target -mlibscl` reports:

| Option | Value |
|---|---|
| `-march` | `armv2` |
| `-mfloat-abi`, `-mfpu` | `hard`, `fpa` |
| `-mapcs-frame` | on: `mov ip, sp` / `stmfd sp!, {..., fp, ip, lr, pc}` on entry |
| stack limit check | on: `cmp sp, sl` / `bllt __rt_stkovf_split_small` |
| `-mpoke-function-name` | on: each function's name sits ahead of it, for backtraces |

Functions return with `ldmea fp, {..., sp, pc}`, which leaves the caller's flags alone. Norcroft's 26-bit code restored them (`^`). C code never depends on that; hand-written assembler that calls a C function and expects its flags back would.

Checked on the built compiler: the `scl/hard/fpa` and `scl-module/hard/fpa` copies of `libgcc.a` hold no `ldrh`, `strh`, `ldrsb`, `ldrsh`, `umull`, `smull`, `bx`, `mrs`, `msr` or `clz`. Long multiplies and divides are calls into libgcc (`__muldi3`, `__divsi3`).

## How the C parts are compiled

`build.sh` holds the commands (`libcc`, `clib`, `clibtest`). The SharedCLibrary is the first C component, and what it needed applies to the rest.

### Options

| Option | Why |
|---|---|
| `-mmodule` | Code inside a module reaches its static data through a relocation offset kept below the stack limit, so one copy of the code serves every client |
| `-ffixed-sl` | The compiler reserves the stack limit register only when stack checks are on. Module code finds its statics through it either way, so it is reserved by hand |
| `-mapcs-stack-check` | Module mode turns the stack limit check off. The library runs on its clients' stacks, which grow in chunks, so it needs the check. `c.alloc` and `c.signal` are compiled without it, as their `#pragma -s1` asks: the allocator is called by the code that grows the stack, and the signal code runs when the stack has overflowed |
| `-mno-poke-function-name` | Function names ahead of each function cost ROM space. The original build left them out too (`cc -ff`) |
| `-O2` | Not `-Os`. See the compiler faults below |
| `-fno-section-anchors` | See the compiler faults below |
| `-ffreestanding` | Stops GCC replacing a library function's body with a call to the same function, or `printf` with `puts` |
| `-fno-common` | Every static lands in `.data` or `.bss`, where the linker script lays out the library's static data |
| `-nostdinc -I<the library's headers>` | The library is compiled against its own headers, not GCC's |
| `-funsigned-bitfields` | A plain `int` bitfield is unsigned to the Norcroft compiler and signed to GCC. `c.math` takes a double apart with bitfields; `floor(2.5)` came out wrong without this |
| `-fno-strict-aliasing -fwrapv -fno-delete-null-pointer-checks` | The sources date from 1988 to 1996 and cast pointers freely, expect signed arithmetic to wrap and read page zero. These switch off the optimisations that assume otherwise |
| `-D__arm -D___type=` | `__arm` is the Norcroft name for the target. `___type` is a Norcroft keyword in the headers' `offsetof` |

### Changes to the compiler's output

`libcc` compiles to assembler, edits it, and assembles the result.

- `[sl, #-536]` becomes `[sl, #-540]`. GCC's module code loads the client's relocation offset. Code in the library uses the library's, the word below it (`_Lib$Reloc$Off` and `_Mod$Reloc$Off` in `s.initmodule`).
- `sym(GOTOFF)` becomes `sym`. GCC writes the address of a static as an offset from the global offset table, and only GCCSDK's linker in its module mode (`--ro-module-reloc`) resolves that to the plain address. Written plain, the constant is the address the static has in the ROM image, and adding the relocation offset gives the client's copy, which is how Norcroft's `-zm` code works.

### Linking

GNU `ld` from the GCCSDK build links the module with `tools/clib.ld`, at the address the module has in the ROM (`tools/mkrom.py --next` works it out from the modules ahead of it). The script defines the `Area$$Base` and `Area$$Limit` symbols Acorn's linker made, puts the kernel's and the library's static data in the order the client stubs expect, and makes the library's static data exactly the size the stubs reserve. Division comes from `libgcc.a`.

A C program held in the ROM (Edit is the first) is a module too: RISC_OSLib's module wrapper is its header and its C files are module code that keeps the client's offset. It links with `tools/romapp.ld` and the ROM stubs (`rlib.s.rl_stub_rm`) at its own address in the ROM, after the library. It calls the library directly, at the addresses in a list `build.sh` makes from the linked library (`PROVIDE(name = address)` for each symbol, which gives way to a symbol of the program's own). Its zero-initialised statics and the stubs' room for the library's statics take no ROM space.

Two modules have headers of their own. Squash's is hand-written and keeps the relocation offset in the word `sl` points at, so its C is compiled for that offset (`modcc 0`). DOSFS's comes from a description file (`cmhg.DOSFShdr`), which CMunge turns into assembler for 26-bit code (`cmunge -tnorcroft -26bit -s`); AsAsm assembles it. Of the C header CMunge writes, only the `#define` lines are used, since its declarations of the module's handlers do not match a 1996 source. The description file carries a `date-string`, so that the build does not stamp the day it ran into the ROM.

A C application on disc links with `tools/app.ld` and the library's stubs (`clib.s.cl_stub_r`) into a plain image that loads and runs at `&8000`.

### Changes to the sources for GCC

Each has a `ROO26:` comment.

| File | Change |
|---|---|
| `clib/h/stdarg` | `va_list` keeps its Norcroft type, a one-element array of `char *`, since programs built with Norcroft pass a pointer to it to `vprintf` and friends. `va_start` uses GCC's built-in to find the first unnamed argument: GCC only puts the unnamed arguments in memory, so the address of the last named one is no guide. It has to be the real `__builtin_va_start`; with `__builtin_next_arg` alone the optimiser makes fixed-argument copies of variadic functions |
| `clib/h/math` | `__d_abs`, `__d_atan`, `__d_sin` and `__d_cos` are inline operations of the Norcroft compiler. Under GCC `fabs` is `__builtin_fabs` and the others are calls to the library |
| `kernel/s/k_body`, `kernel/s/k_mod_r` | GCC's functions return without restoring the caller's flags; Norcroft's 26-bit code restored them. Four places in the library's assembler relied on getting flags back from a C function or a client's function: the calls to client handlers (`CallClient`, `_kernel_call_client`, `FindAndCallHandlers`), the loop that frees stack chunks, and the return from a function that grew the stack, which read the Z flag to tell which calling standard the function used. Each now tests again after the call, and the stack return has a second entry point for the old calling standard |
| `rlib/c/wimp` | `#include "trace .h"` loses its space. RISC_OSLib's other 48 C files compile as they are |
| `clib/s/cl_entries` | The library held a second `bsearch` compiled for the old calling standard (`cc -zkA`). GCC cannot produce that, so old clients reach the one `bsearch` through the calling standard veneer, as they already do for `qsort` |

Programs that call the library still get their flags back from the assembler parts (the SWI veneers, `memcpy`, the maths entry points) and not from the C parts. Norcroft's code never keeps a flag across a call, so C programs do not notice. Hand-written assembler that does would.

### Compiler faults found

- **`-Os` pushes every register.** In a function with no frame pointer, the prologue code that pads the register list to make stack room (`arm_expand_prologue`, the `optimize_size` branch) can compute a negative frame size, and the mask it builds from that covers all sixteen registers, `sp` and `pc` included. `c.alloc` (`internal_coalesce`) triggers it, and the compiler then overruns a 100-byte buffer writing the instruction out and aborts. `-O2` does not take that path.
- **Section anchors with module data.** At `-O1` and above `c.signal` stops the compiler with "insn does not satisfy its constraints" in `reload_cse_simplify_operands`, on a store through a section anchor plus the relocation offset. `-fno-section-anchors` avoids it.

### Testing

`tests/clibtest.c` calls into each part of the library (formatted output and input, variadic calls, the allocator, sorting, `setjmp`, strings, maths, files, time, signals, a 200K deep recursion to grow the stack, `system`, `atexit`) and prints what failed.

```bash
sh build.sh clibtest
```

The program is `build/A5000/clibtest,ff8`. Run it from a filing system it can write to.

## Building the compiler

GCC 4.7 does not build with a current host compiler, so it is built in a container running Ubuntu 14.04, the system GCCSDK's own Dockerfile names. It needs Docker, Subversion and wget, about 6GB of disc, and takes about a quarter of an hour on 12 cores.

```bash
sh toolchain/fetch.sh /some/work/dir
```

```bash
docker build -t roo26-gcc /some/work/dir
```

`fetch.sh` checks out GCCSDK's build recipe at revision 7800 and downloads the source archives the recipe needs, each checked against `SHA256SUMS`. The recipe itself checks GCC out from the closed `gcc-4_7-branch` of GCC's Subversion repository during the build, so the build needs the network.

The compiler ends up in the image at `/gccsdk/cross/bin` (`arm-unknown-riscos-gcc` and binutils), with GCCSDK's tools beside it (`cmunge`, `elf2aif`, `asasm`). To use it outside the container, copy it out; it runs from any folder:

```bash
docker create --name roo26-gcc-x roo26-gcc && docker cp roo26-gcc-x:/gccsdk/cross ./cross && docker cp roo26-gcc-x:/gccsdk/env ./env && docker rm roo26-gcc-x
```

`build.sh` takes the compiler from `GCC` (the path of `arm-unknown-riscos-gcc`) or from `PATH`.

## What was changed from stock GCCSDK

All three changes are in `toolchain/Dockerfile`.

- **C only.** `GCC_LANGUAGES` is `c`, not `c,c++`.
- **No loop optimiser libraries.** `GCC_USE_PPL_CLOOG` is `no`. PPL and CLooG take longer to build than GCC and ROO26 gains nothing from them.
- **The build is retried.** `build-world` runs up to three times. A parallel build of GCC 4.7 can compile fixincludes' generated `fixincl.x` while it is still being written (`'apz' undeclared`); the next pass finds the file complete and carries on.

## AsAsm

AsAsm is built from `svn://svn.riscos.info/gccsdk/trunk/tools/asasm` in the usual way (`autoreconf --install`, `configure --target=arm-unknown-riscos --disable-building-tools`, `make`). The GCC image also holds a copy at `/gccsdk/env/bin/asasm`.

The RISC OS 3.60 sources were written for Acorn's AAsm, and AsAsm differs from it in ways that matter. `tools/fixcase.py` normalises the imported sources for the first three; the rest are source edits marked `ROO26:`.

| Difference | Effect | Handling |
|---|---|---|
| File names are case sensitive on Linux | `GET s.vdu.VduDriver` misses `s/vdu/vdudriver` | `fixcase.py` rewrites the names |
| A final backslash continues the line | The next line is swallowed, silently | `fixcase.py` adds a space |
| A backslash in a string starts a C escape | `"\"` is a string with no end | `fixcase.py` writes `&5C` |
| A branch over 32MB is an error | Code copied to page zero that branches into ROM | A `BWrap` macro writes the instruction word |
| `LDR r, =expr` with a forward-referenced `expr` recurses without end | The assembler crashes | Constants are defined ahead of use |
| `[Rn], #0` is assembled as `[Rn]` | Same behaviour, different encoding from the original ROMs | None needed |
| `LEADR`, `KEEP` are not accepted in AAsm mode | Error | `LEADR` is an empty macro in `Hdr:ListOpts` |
| Lower case mnemonics are instructions | The sources define macros called `mrs` and `msr` | Assembled with `-Uppercase` |
