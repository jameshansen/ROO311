<p align="center"><img src="icon.png" width="128" alt="ROO311 icon"></p>

<h1 align="center">ROO311</h1>

<p align="center"><b>RISC OS 3.11 for the Archimedes, built from open sources.</b><br>A free ROM image that takes the place of the commercial RISC OS 3.11 ROM in an Archimedes emulator, built from the RISC OS Open sources with open tools.</p>

<p align="center"><a href="../../releases/latest"><b>Download the ROM image</b></a></p>

<p align="center">Discord: <a href="https://discord.gg/88VzuWSYUc">https://discord.gg/88VzuWSYUc</a></p>

![The ROO311 desktop in a 640 by 480 mode with 256 colours, the Apps folder and Configure open](docs/desktop.png)

## What it does

An Archimedes emulator needs a RISC OS ROM image to start, and the RISC OS 3.11 one is commercial. ROO311 is a free ROM image that goes in its place. It starts an A5000 in the desktop with no hard disc, boots a game from its floppy image, and has Chars, Help, Edit, Draw, Paint, SciCalc and Configure in the ROM.

It is a port of RISC OS Open to 26-bit machines. It looks and works like RISC OS Open, and it aims to run what RISC OS 3.11 ran.

The whole thing is one 2MB file. It is unfinished, and [What works](#what-works) says how far it has got.

## The original ROM

RISC OS 3.11 is the last version of RISC OS that Acorn released for the Archimedes. Its ROM image is commercial. [RISC OS Open](https://www.riscosopen.org) publishes the sources of later versions, and the oldest of those is RISC OS 3.60 of 1995.

ROO311 is built from those sources. The kernel and most modules are RISC OS 3.60's, the last to carry the code for the Archimedes's MEMC1 memory controller, and a few parts come from the current sources. Every file in the ROM comes from the RISC OS Open repositories or was written for this project. Nothing is copied from a commercial ROM. Where a commercial ROM was consulted to settle how RISC OS 3.11 behaved, a comment in the source names the ROM and the address.

ROO311 is an unofficial project and is not affiliated with RISC OS Open Ltd.

## Features

- **A drop-in ROM image.** One 2MB file, the size an A5000 and Arculator take, in place of the RISC OS 3.11 one.
- **Open from end to end.** The sources are RISC OS Open's, the assembler is AsAsm and the C compiler is GCC. Nothing proprietary is needed to build it.
- **The RISC OS Open look.** 3D windows, Homerton as the desktop font, textured backgrounds, high resolution icons, the multi-coloured cog on the icon bar and the RISC OS Open start-up banner.
- **Applications in the ROM.** Chars, Help, Edit, Draw, Paint, SciCalc and Configure run from the Apps folder.
- **No hard disc needed.** The machine starts in the desktop from the ROM alone. Hold Shift as it starts and it boots the floppy disc in drive 0, which is how Blaston (1991) starts from its floppy image.
- **Old programs run.** The SharedCLibrary is in the ROM with RISC_OSLib inside it, as RISC OS 3 had it. Battle Chess (1992), a C game built with the Norcroft compiler, runs on it.
- **RISC OS 3.11's settings.** A CMOS reset gives RISC OS 3.11's defaults. Configure keeps the monitor type and the desktop's mode in the CMOS RAM, and its Screen window changes the screen at once.
- **Fits in 2MB.** The message files are tokenised and the BASIC applications crunched and squished, as the original build did. 6K is spare.

![Configure's Screen window on the ROO311 desktop](docs/configure-screen.png)

## What works

The ROM boots in Arculator, driven by a script, on an A5000-style machine (ARM3, MEMC1a, 82C711, 4MB).

| Works | Not yet |
|---|---|
| Kernel on MEMC1/IOC/VIDC1, 26-bit throughout | DOSFS is in the ROM but has not read a DOS disc yet |
| 70 ROM modules initialise | Alarm (its machine code helper is assembled by a BASIC program, and the image has no room left for it) |
| Configure runs from the Apps folder. Its Screen window sets the monitor type and the desktop's mode, and the screen changes at once and comes back the same after a reset | Configure's settings that live in a boot application on disc, which are the desktop font, the RAM disc and the background texture |
| | Tactic does not start. It restores its saved configuration from the wrong disc data |
| Supervisor prompt, keyboard, mouse, `*` commands | Palette utility on the icon bar |
| BBC BASIC V 1.14 with graphics, FPEmulator 4.39 | Printing modules, Econet and NetFS |
| Desktop with the RISC OS Open look | Power-on self test |
| Filer operations through Filer_Action (delete and count tried) | Hard disc access is untested |
| Chars, Help, Edit, Draw, Paint and SciCalc run from the Apps folder | Sound has not been listened to |
| Outline fonts (Font Manager and ROM fonts), scaled sprites (SpriteExtend), Squash | Copy-protected floppy images (they need a track-level image format) |
| ADFS floppy access on the 82C711, including `ADFS_DiscOp` writes | Most games are untried |
| HostFS from Arculator's support ROM (extension ROM loading) | Other emulators and real hardware are untried |
| CMOS defaults of RISC OS 3.11 | |
| Blaston (1991) boots from its floppy image and runs, with no ADFFS | |
| SharedCLibrary 4.79 with RISC_OSLib inside it, the C parts compiled with GCC. A test program passes every check | |
| Battle Chess (1992) runs on that library | |

The image uses 2,090,888 of the 2MB (2,097,152 bytes). A5000 hardware and Arculator both stop at 2MB.

## Install

1. Download `rom` from the [latest release](../../releases/latest), or build it as [Building the ROM](#building-the-rom) describes.
2. In Arculator's folder, open `roms/riscos311` and move the files in it somewhere else. Arculator loads every file in that folder, in name order, as one ROM.
3. Copy `rom` into `roms/riscos311`.
4. Set up an A5000 with RISC OS 3.11 as its ROM, and start it.

| Machine | Notes |
| --- | --- |
| A5000 (ARM3, MEMC1a, 82C711 floppy controller, 4MB) | The machine it is built for and tested on. |
| Other Archimedes models | Untried. |

With an empty CMOS RAM the machine has no filing system configured. Hold Delete as it starts to set RISC OS 3.11's defaults, and it then starts in the desktop.

## Using it

The machine starts in the desktop. The Apps icon on the icon bar opens the applications in the ROM, and the cog is the Task Manager.

| Key | Action |
| --- | --- |
| Delete, held as the machine starts | Set the CMOS RAM to RISC OS 3.11's defaults |
| Shift, held as the machine starts | Boot the floppy disc in drive 0 |
| F12 | Open a command line at the foot of the desktop. Return on an empty line closes it |
| Ctrl+Break | Reset the machine |

Configure sets the machine up. Its Screen window has menus for the monitor type, the colours and the resolution. **Set** changes the screen at once and keeps the choice for the next start, and **Cancel** puts back what was there.

Files reach the machine on a floppy image or through HostFS, which Arculator's support ROM provides.

## How it works

The kernel and most modules are the RISC OS 3.60 sources, the oldest RISC OS Open publishes. `Sources/UPSTREAM` records the repository and commit behind each folder. The kernel's MEMC1 build path had not been assembled since RISC OS 3.5. It assembles and runs again, and `git log -- Sources/Kernel` lists each repair. Changes to imported sources carry a comment starting `ROO311:` that says what changed.

The components listed in `Sources/NEWER` come from the current RISC OS Open sources and build against current headers (`Sources/Headers5`). FPEmulator is one. The Desktop module is another, for its start-up banner, which reads RISC OS and not RISC OS 5. The cog on the icon bar is the current one too (`Sources/Desktop/Wimp5`), put into the sprite form the rest of the ROM's icons have. It shows its eight colours in a 256 colour mode. In a 16 colour mode its purple and pink teeth are grey, the nearest the desktop's palette has.

The assembler sources were written for Acorn's AAsm and ObjAsm and are assembled with AsAsm. The C parts were written for the Norcroft compiler and are compiled with GCC 4.7.4, the last GCC that can target an ARM2 or ARM3. They are the SharedCLibrary with RISC_OSLib inside it, Edit, Draw, Paint, Configure, Filer_Action, Squash and DOSFS. Each application is a module in the ROM that calls the library in the ROM directly, as RISC OS 3 held Edit, Draw and Paint. [toolchain/README.md](toolchain/README.md) has the compiler options, the changes the sources needed and the two compiler faults that had to be fixed.

Fitting 2MB takes the methods the original build used. The message files are tokenised against the kernel's dictionary and Help's tokens. Chars and Help, which are BASIC programs, go through BASIC's `CRUNCH` and the build's Squish tool, both ported to Python here. Together that frees 59K, which is what lets Configure in. ColourTrans's ready-made tables for plotting 16 and 32 bit per pixel sprites are left out (83K), and it builds a table when one is first wanted. SpriteExtend is built with its all-assembler code generator and no JPEG, as RISC OS 3.11's was. The ROM has one set of icons, the high resolution one, and in a mode whose pixels are not square (mode 12 on a TV-standard monitor) the Window Manager scales them.

Configure is the RISC OS 3.6 one. It was a disc application that a boot application on disc started. In the ROM it starts without the boot application, and what it kept in the CMOS RAM works. Its Screen window keeps the monitor type and the desktop's mode in the CMOS RAM too, as RISC OS 3.11 did (`*Configure MonitorType` and `WimpMode`). Its menus of colours and resolutions offer the numbered modes the chosen monitor can show, where they had come from the monitor definition files of later machines. What it kept in files of the boot application has nowhere to go yet.

The calculator is SciCalc, the one RISC OS Open publishes. It was a disc application that needed BASIC64. In the ROM it runs on the ROM's BASIC, to 9 figures, unless BASIC64 has been loaded.

On an IOC machine a CMOS reset gives the RISC OS 3.11 settings for how the machine starts (drive 0, NoBoot, mouse step 3) and RISC OS Open's for how the desktop looks. The Podule manager is arranged for 4 podules and extension ROMs, ADFS leaves out big disc support where the ST506 driver is present, and SoundDMA has only the 8-bit SWIs.

The kernel's workspace layout below `&1000` and in the VDU driver follows the RISC OS 3.60 sources, which moved some VDU variables relative to RISC OS 3.11. Software that reads those by address and not through `OS_ReadVduVariables` will see different values.

## Building the ROM

The build runs on Linux and needs AsAsm from GCCSDK (`svn://svn.riscos.info/gccsdk/trunk/tools/asasm`), `binutils-arm-none-eabi` and Python 3. The C parts need GCC 4.7.4 for RISC OS. [toolchain/README.md](toolchain/README.md) says how to build both and what each one needs.

```bash
ASASM=/path/to/asasm GCC=/path/to/arm-unknown-riscos-gcc sh build.sh
```

The ROM is `build/A5000/rom`. Each module's ELF file beside it holds source line numbers.

| File | What it does |
| --- | --- |
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
| `tools/basic.py` | Lists a tokenised BBC BASIC file, crunches one as BASIC's `CRUNCH` does and squishes one as the build's Squish tool does |
| `tools/sprites.py` | Makes the ROM's sprite file from the sources' sprite files |

## Pi Projects

ROO311 comes from the same hands as four projects for the Raspberry Pi. One is a utility for the desktop, and three bring favourite old free games to the Pi.

| Project | What it is |
| --- | --- |
| [PiOSBeachBall](https://github.com/jameshansen/PiOSBeachBall) | A spinning beachball pointer that shows when an app is loading. |
| [PiKnytt](https://github.com/jameshansen/PiKnytt) | Knytt, the 2006 exploration platformer by Nifflas, installed and ready to play. |
| [PiKlassOf99](https://github.com/jameshansen/PiKlassOf99) | Klass of 99, Richard Jordan's Skool Daze remake, installed and ready to play. |
| [PiPakoon](https://github.com/jameshansen/PiPakoon) | Pakoon 0, 1 and 2, Mikko Oksalahti's driving games, built for the Pi with a launcher to pick between them. |

## AI use disclosure

ROO311 was built using [Claude Code](https://claude.com/claude-code) with Claude Fable 5.2.

## Credits

RISC OS was written by Acorn Computers. The sources ROO311 is built from are published by [RISC OS Open](https://www.riscosopen.org), and the cog on the icon bar and the start-up banner are theirs.

The ROM is assembled with AsAsm and compiled with GCC 4.7.4 for RISC OS, both from [GCCSDK](https://www.riscos.info/index.php/GCCSDK). It is tested in [Arculator](https://github.com/sarah-walker-pcem/arculator) by Sarah Walker.

The icon is the cog on the ROM's own icon bar.

## Licence

The RISC OS sources in `Sources/` are free software under the Apache License, version 2.0. Each component carries its own `LICENSE` file, and three of them name other terms for some of their files, the New BSD licence and those of the Independent JPEG Group. The changes made to the sources here are under the same licences.
