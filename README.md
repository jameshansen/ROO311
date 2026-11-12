# RISC OS Open 26-bit (ROO26)

A RISC OS ROM for Archimedes machines with an ARM3 and MEMC1 (an A5000 is the reference machine), built from the RISC OS Open sources with open tools. It is a port of RISC OS Open to 26-bit machines: it looks and works like RISC OS Open, runs what RISC OS 3.11 ran, needs no hard disc, and fits a 2MB ROM. It is a free replacement for the commercial RISC OS 3 ROMs in Archimedes emulators.

## Status

The ROM boots in Arculator on an A5000-style machine (ARM3, MEMC1a, 82C711, 4MB).

| Works | Not yet |
|---|---|
| Kernel on MEMC1/IOC/VIDC1, 26-bit throughout | DOSFS is in the ROM but has not read a DOS disc yet |
| 70 ROM modules initialise | Alarm (its machine code helper is assembled by a BASIC program, and the image has no room left for it) |
| Configure runs from the Apps folder. Its Screen window sets the monitor type and the desktop's mode: the screen changes at once and comes back the same after a reset | Configure's settings that live in a boot application on disc: the desktop font, the RAM disc, the background texture |
| | Tactic does not start: it restores its saved configuration from the wrong disc data |
| Supervisor prompt, keyboard, mouse, `*` commands | Palette utility on the icon bar |
| BBC BASIC V 1.14 with graphics, FPEmulator 4.39 | Printing modules, Econet and NetFS |
| Desktop with the RISC OS Open look: 3D windows, Homerton, textured backgrounds, high resolution icons, the cog on the icon bar, the RISC OS Open start-up banner |
| Filer operations through Filer_Action (delete and count tried) | Power-on self test |
| Chars, Help, Edit, Draw, Paint and SciCalc run from the Apps folder | Hard disc access is untested |
| Outline fonts (Font Manager and ROM fonts), scaled sprites (SpriteExtend), Squash | Sound has not been listened to |
| ADFS floppy access on the 82C711, including `ADFS_DiscOp` writes | Copy-protected floppy images (they need a track-level image format) |
| HostFS from Arculator's support ROM (extension ROM loading) | Most games are untried |
| CMOS defaults of RISC OS 3.11 | |
| Blaston (1991) boots from its floppy image and runs, with no ADFFS: Shift at power on starts it | |
| SharedCLibrary 4.79 with RISC_OSLib inside it, the C parts compiled with GCC: a test program passes every check | |
| Battle Chess (1992), a C game built with the Norcroft compiler, runs on that library | |

The image uses 2,090,456 of the 2MB (2,097,152 bytes), with 7K to spare. A5000 hardware and Arculator both stop at 2MB.

## Where everything comes from

Every file in the ROM comes from the RISC OS Open repositories or was written for this project. Nothing is copied from a commercial ROM. `Sources/UPSTREAM` records the repository and commit behind each folder.

- The kernel and most modules are the RISC OS 3.60 sources, the oldest RISC OS Open publishes and the last to carry the MEMC1 code paths.
- Components listed in `Sources/NEWER` come from the current RISC OS Open sources and build against current headers (`Sources/Headers5`). FPEmulator is the first.
- SpriteExtend is built with its all-assembler code generator and no JPEG, as RISC OS 3.11's was.
- The calculator is SciCalc, the one RISC OS Open publishes. It was a disc application that needed BASIC64; in the ROM it runs on the ROM's BASIC, to 9 figures, unless BASIC64 has been loaded.
- The message files are tokenised against the kernel's dictionary and Help's tokens, and Chars and Help are crunched and squished, as the original build did. Together that frees 59K, which is what lets Configure in.
- Configure is the RISC OS 3.6 one. It was a disc application that a boot application on disc started; in the ROM it is a module like Edit, Draw and Paint, and it starts without the boot application. What it kept in the CMOS RAM works. Its Screen window keeps the monitor type and the desktop's mode in the CMOS RAM too, as RISC OS 3.11 did (`*Configure MonitorType` and `WimpMode`): its menus of colours and resolutions offer the numbered modes the chosen monitor can show, where they had come from the monitor definition files of later machines. What it kept in files of the boot application (the desktop font, the RAM disc, the background texture) has nowhere to go yet.
- ColourTrans's ready-made tables for plotting 16 and 32 bit per pixel sprites are left out of the ROM (83K). It builds a table when one is first wanted.
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
| `tools/msgtok.py` | Tokenises the ROM's message files, as the original build's MsgTok tools did |
| `tools/basic.py` | Lists a tokenised BBC BASIC file; crunches one as BASIC's `CRUNCH` does and squishes one as the build's Squish tool does |

## Differences from the imported sources that matter

- The kernel's MEMC1 build path had not been assembled since RISC OS 3.5. It assembles and runs again; `git log -- Sources/Kernel` lists each repair.
- On an IOC machine a CMOS reset gives the RISC OS 3.11 settings for how the machine starts (drive 0, NoBoot, mouse step 3) and RISC OS Open's for how the desktop looks.
- The ROM has one set of icons, the high resolution one. In a mode whose pixels are not square (mode 12 on a TV-standard monitor) the Window Manager scales them.
- The Desktop module is the current RISC OS Open one, for its banner. The banner reads RISC OS, not RISC OS 5.
- The Podule manager is arranged for 4 podules and extension ROMs, ADFS leaves out big disc support where the ST506 driver is present, and SoundDMA has only the 8-bit SWIs.
- The kernel's workspace layout below `&1000` and in the VDU driver follows the RISC OS 3.60 sources, which moved some VDU variables relative to RISC OS 3.11. Software that reads those by address rather than through `OS_ReadVduVariables` will see different values.
