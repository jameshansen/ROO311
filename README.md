# RISC OS Open 26-bit (ROO26)

A RISC OS ROM for Archimedes machines with an ARM3 and MEMC1 (an A5000 is the reference machine), built from the RISC OS Open sources with open tools. It is a free replacement for the commercial RISC OS 3 ROMs in Archimedes emulators, and it fits a 2MB ROM.

## Status

The ROM boots in Arculator on an A5000-style machine (ARM3, MEMC1a, 82C711, 4MB).

| Works | Not yet |
|---|---|
| Kernel on MEMC1/IOC/VIDC1, 26-bit throughout | The other C programs: Draw, Paint, Filer_Action, Squash, DOSFS |
| 64 ROM modules initialise | Alarm (its machine code helper is assembled by a BASIC program), Calc, Configure |
| Supervisor prompt, keyboard, mouse, `*` commands | Palette utility on the icon bar |
| BBC BASIC V 1.14 with graphics, FPEmulator 4.39 | Printing modules, Econet and NetFS |
| Desktop with the RISC OS 3 look: icon bar, Filer windows, error boxes, Task Manager | Power-on self test |
| Chars, Help and Edit run from the Apps folder | Hard disc access is untested |
| Outline fonts (Font Manager and ROM fonts), scaled sprites (SpriteExtend) | Sound has not been listened to |
| ADFS floppy access on the 82C711, including `ADFS_DiscOp` writes | Copy-protected floppy images (they need a track-level image format) |
| HostFS from Arculator's support ROM (extension ROM loading) | Most games are untried |
| CMOS defaults of RISC OS 3.11 | |
| Blaston (1991) boots from its floppy image and runs, with no ADFFS | |
| SharedCLibrary 4.79 with RISC_OSLib inside it, the C parts compiled with GCC: a test program passes every check | |
| Battle Chess (1992), a C game built with the Norcroft compiler, runs on that library | |

The image uses 1.61MB of the 2MB.

## Where everything comes from

Every file in the ROM comes from the RISC OS Open repositories or was written for this project. Nothing is copied from a commercial ROM. `Sources/UPSTREAM` records the repository and commit behind each folder.

- The kernel and most modules are the RISC OS 3.60 sources, the oldest RISC OS Open publishes and the last to carry the MEMC1 code paths.
- Components listed in `Sources/NEWER` come from the current RISC OS Open sources and build against current headers (`Sources/Headers5`). FPEmulator is the first.
- SpriteExtend is built with its all-assembler code generator and no JPEG, as RISC OS 3.11's was.
- Changes to imported sources carry a comment starting `ROO26:` that says what changed. Where a commercial ROM was consulted to settle how something behaved, the comment names the ROM and the address.

## Building

The build runs on Linux and needs AsAsm from GCCSDK (`svn://svn.riscos.info/gccsdk/trunk/tools/asasm`), `binutils-arm-none-eabi` and Python 3. The C parts need GCC 4.7.4 for RISC OS. [toolchain/README.md](toolchain/README.md) says how to build both and what each one needs.

```bash
ASASM=/path/to/asasm GCC=/path/to/arm-unknown-riscos-gcc sh build.sh
```

The ROM is `build/A5000/rom`. Each module's ELF file beside it holds source line numbers.

| File | What it does |
|---|---|
| `build.sh` | Assembles the kernel and modules, gathers resources, joins the ROM |
| `Sources/MODULES` | The modules after the kernel, in ROM order |
| `tools/mkres.py` | Gathers each component's messages, templates and sprites into the Messages module |
| `tools/mkrom.py` | Joins the kernel and modules into the image, and says what address a module will get |
| `tools/clib.ld`, `tools/romapp.ld`, `tools/app.ld` | Linker scripts for the SharedCLibrary module, a C program in the ROM and a C application on disc |
| `tests/clibtest.c` | A test of the SharedCLibrary (`sh build.sh clibtest`) |
| `tools/prepare.py`, `tools/tokhelp.py` | Make the source files the original build generated under RISC OS |
| `tools/fixcase.py` | Normalises imported sources for AsAsm on Linux (file name case, backslashes) |
| `tools/romdiff.py` | Lines a built image up against a reference ROM and shows the code that differs |
| `tools/whereis.py` | Names the module and source line behind a ROM address |
| `tools/basic.py` | Lists a tokenised BBC BASIC file |

## Differences from the imported sources that matter

- The kernel's MEMC1 build path had not been assembled since RISC OS 3.5. It assembles and runs again; `git log -- Sources/Kernel` lists each repair.
- On an IOC machine a CMOS reset gives the RISC OS 3.11 settings (drive 0, NoBoot, 32K font cache, flat desktop in the system font, mouse step 3).
- The Podule manager is arranged for 4 podules and extension ROMs, ADFS leaves out big disc support where the ST506 driver is present, and SoundDMA has only the 8-bit SWIs.
- The kernel's workspace layout below `&1000` and in the VDU driver follows the RISC OS 3.60 sources, which moved some VDU variables relative to RISC OS 3.11. Software that reads those by address rather than through `OS_ReadVduVariables` will see different values.
