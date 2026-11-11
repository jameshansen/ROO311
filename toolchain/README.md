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

## Building the compiler

GCC 4.7 does not build with a current host compiler, so it is built in a container running Ubuntu 14.04, the system GCCSDK's own Dockerfile names. It needs Docker, Subversion and wget, about 6GB of disc, and takes about a quarter of an hour on 12 cores.

```bash
sh toolchain/fetch.sh /some/work/dir
```

```bash
docker build -t roo26-gcc /some/work/dir
```

`fetch.sh` checks out GCCSDK's build recipe at revision 7800 and downloads the source archives the recipe needs, each checked against `SHA256SUMS`. The recipe itself checks GCC out from the closed `gcc-4_7-branch` of GCC's Subversion repository during the build, so the build needs the network.

The compiler ends up in the image at `/gccsdk/cross/bin` (`arm-unknown-riscos-gcc` and binutils) with GCCSDK's tools in `/gccsdk/env/bin` (`cmunge`, `elf2aif`, `asasm`). To use it outside the container, copy it out; it runs from any folder:

```bash
docker create --name roo26-gcc-x roo26-gcc && docker cp roo26-gcc-x:/gccsdk/cross ./cross && docker cp roo26-gcc-x:/gccsdk/env ./env && docker rm roo26-gcc-x
```

`build.sh` takes the compiler from `GCCSDK` (the `cross/bin` folder) or from `PATH`.

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
