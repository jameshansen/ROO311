<p align="center"><img src="icon.png" width="128" alt="ROO311 icon"></p>

<h1 align="center">ROO311</h1>

<p align="center"><b>RISC OS Open for the Archimedes, compatible with RISC OS 3.11.</b><br>A free ROM image built from the RISC OS Open sources with open tools, which can take the place of the commercial RISC OS 3.11 ROM in an Archimedes emulator.</p>

<p align="center"><a href="../../releases/latest"><b>Download the ROM image</b></a></p>

<p align="center">Discord: <a href="https://discord.gg/88VzuWSYUc">https://discord.gg/88VzuWSYUc</a></p>

![The ROO311 desktop in a 640 by 480 mode with 256 colours, the Apps folder and Configure open](docs/desktop.png)

## What it does

ROO311 is a port of RISC OS Open to the 26-bit Acorn Archimedes. It looks and works like RISC OS Open, and it's built to be compatible with RISC OS 3.11, so the aim is for it to run what RISC OS 3.11 ran.

An Archimedes emulator needs a RISC OS ROM image before it can start, and the RISC OS 3.11 one is commercial. ROO311 is a free and open ROM image that an emulator can load where it would load that one, so an emulated A5000 starts in the desktop with no commercial ROM and no hard disc. It boots a game from its floppy image, and it has Chars, Help, Edit, Draw, Paint, SciCalc and Configure in the ROM.

The whole ROM is one 2MB file. It's unfinished, see [What works](#what-works).

## Why

I have been creating a number of tools to allow the easy launching of some of my, and my kids' favourite games on the Raspberry Pi, such as [Knytt](https://github.com/jameshansen/PiKnytt) and [Klass of 99](https://github.com/jameshansen/PiKlassOf99), and I have been sharing these projects here for other fans of these lesser known titles. I wanted to add the Risc OS version of Lemmings, along with other games freely released on [JASPP](https://forums.jaspp.org.uk/forum/index.php) to that list. The problem is that these old games require a commercial Risc OS 3.11 ROM, so the ultimate purpose of this project to eliminate that block to releasing a future tool to do this onto GitHub.

After starting this project I learned of a similar project, [arclibre](https://github.com/acorn-playground/arclibre/) which aims to do the same thing, with a slightly different approach.

## The original ROM

RISC OS 3.11 is the last version of RISC OS that Acorn released for the Archimedes, and its ROM image is commercial. [RISC OS Open](https://www.riscosopen.org) publishes the sources of later versions, the oldest of which is RISC OS 3.60 from 1995.

ROO311 is built from those sources. The kernel and most modules are RISC OS 3.60's, which was the last version to carry the code for the Archimedes's MEMC1 memory controller, and a few parts come from the current sources. Every file in the ROM comes from the RISC OS Open repositories or was written for this project, and nothing is copied from a commercial ROM.

ROO311 is an unofficial project and isn't affiliated with RISC OS Open Ltd.

## How the commercial ROMs were used

The commercial ROMs were available throughout development, and this section sets out exactly how they were used. No code or data in ROO311 is copied from them. Some facts about RISC OS 3.11 were taken from its ROM, and ROO311 was tested against that ROM. The lists below cover everything ROO311 takes from the commercial ROMs and every fault they helped find, ordered from observing the ROM as it runs to disassembling its code.

The ROMs helped find 6 faults. Of those, 4 were real faults in the published source, all in code for these older machines that nothing had built since RISC OS 3.5. The other 2 were caused by this project's own build tools and setup.

### Watching RISC OS 3.11 run in the emulator

Nothing in this group looks inside the ROM. It's what anyone can see by using a RISC OS 3.11 machine.

- **The settings a CMOS reset gives.** The CMOS was reset under 3.11 (Delete held at power on) and the settings were read back. From that, ROO311's reset table for these machines sets drive 0, NoBoot and mouse step 3, and leaves out the Risc PC's later settings. The source's own comments record that Boot and drive 4 replaced NoBoot and drive 0 in September 1993, so mouse step 3 is the only value that depends on the readback.
- **Testing.** The same games, commands and CMOS resets were run on both ROMs and the screens were compared. That's how [What works](#what-works) was checked. Where ROO311 misbehaved, the same run on 3.11 showed the correct behaviour.

### Reading names and text out of the ROM file

This group reads the ROM image as data, and no code is disassembled. The same information is shown by `*ROMModules` and `*Help` on a real machine, or is visible on its screen.

- **The module list and its order.** A script read the list of modules from the 3.11 ROM image. `Sources/MODULES` builds 70 of those modules in the same order, except Squash, and the list determined which components were imported. The list is also public, and a [listing of `*ROMModules` on 3.11](https://www.chiark.greenend.org.uk/~theom/riscos/mods/311.html) gives the same order.
- **The date in DOSFS's help string.** The header tool stamps the build date into this string, which made every build different. The string was given a fixed date instead, 01 Mar 1995, which is the date DOSFS 0.62 carries in the 3.60 ROM. Any fixed date would have worked. This is one of the 2 faults caused by the build setup.
- **The teletext font.** One character was missing from ROO311's font, and comparing its font table with 3.11's showed which one. The cause was the assembler, AsAsm, which treats a comment ending in a backslash as continuing on the next line, so one line of the font was lost. The font data itself comes from the source. This is the other fault caused by the build tools.

### Disassembling code

These are the cases where the ROM's code was read. In each case the fix was written for ROO311, and a comment in the source notes that the ROM was consulted.

- **The first word of the ROM** (3.11, `&03800000`). Some games reset the machine by copying this word to address 0 and jumping to it. With the word the later source produces, the machine was only partly reset. The word in the 3.11 ROM was read and found to be a branch that still works from address 0. ROO311 now has a branch of the same kind, calculated from its own reset address. This was a real fault, because the later source had changed how a reset is entered.
- **`*ScreenLoad`'s palette** (3.11, `&0381C4C0`). A 256 colour picture loaded with a black palette. The routine in 3.11 takes the sprite pointer from R2. ROO311's routine read it from a register that is never set on a kernel without mode selectors. The fix uses R2, and the fault can be seen from the source alone. This was a real fault.
- **Changing a dynamic area's size** (3.11, `&0380AAC0`). The kernel reported CAM Map Corrupt at start-up. Comparing its code with 3.11's showed that a branch had ended up inside the wrong conditional case, so a MEMC1 build returned to a stale address. The branch was moved back to the correct place. This was a real fault.
- **The Podule manager's loop over extension ROMs.** The machine hung at start-up with an extension ROM fitted. 3.11's Podule module was disassembled to compare, and it has no such loop. The loop in ROO311 kept its count in a register that the routines it calls overwrite, and the fix is new code. This was a real fault, in code that the Risc PC builds had switched off.
- **Where the VDU variables are.** Comparing the kernel's code with 3.11's showed that some VDU variables are at different addresses, which is recorded under [How it works](#how-it-works).

## Features

- **A drop-in ROM image.** It's one 2MB file, the size an A5000 and Arculator take, so it goes in place of the RISC OS 3.11 one.
- **Open from end to end.** The sources are RISC OS Open's, the assembler is AsAsm and the C compiler is GCC, so nothing proprietary is needed to build it.
- **The RISC OS Open look.** It has 3D windows, Homerton as the desktop font, textured backgrounds, high resolution icons, the multi-coloured cog on the icon bar and the RISC OS Open start-up banner.
- **Applications in the ROM.** Chars, Help, Edit, Draw, Paint, SciCalc and Configure run straight from the Apps folder.
- **No hard disc needed.** The machine starts in the desktop from the ROM alone, and holding Shift as it starts boots the floppy disc in drive 0, which is how Blaston (1991) starts from its floppy image.
- **Old programs run.** The SharedCLibrary is in the ROM with RISC_OSLib inside it, the way RISC OS 3 had it, and Battle Chess (1992), a C game built with the Norcroft compiler, runs on it.
- **RISC OS 3.11's settings.** A CMOS reset gives RISC OS 3.11's defaults, Configure keeps the monitor type and the desktop's mode in the CMOS RAM, and its Screen window changes the screen straight away.
- **Fits in 2MB.** The message files are tokenized and the BASIC applications crunched and squished, the same way the original build did it, which leaves 6K spare.

![Configure's Screen window on the ROO311 desktop](docs/configure-screen.png)

## What works

The ROM has been booted in Arculator on an A5000-style machine (ARM3, MEMC1a, 82C711, 4MB), driven by a script.

### Works

- Kernel on MEMC1/IOC/VIDC1, 26-bit throughout
- 70 ROM modules initialize
- Configure runs from the Apps folder. Its Screen window sets the monitor type and the desktop's mode, and the screen changes at once and comes back the same after a reset
- Supervisor prompt, keyboard, mouse, `*` commands
- BBC BASIC V 1.14 with graphics, FPEmulator 4.39
- Desktop with the RISC OS Open look
- Filer operations through Filer_Action (delete and count tried)
- Chars, Help, Edit, Draw, Paint and SciCalc run from the Apps folder
- Outline fonts (Font Manager and ROM fonts), scaled sprites (SpriteExtend), Squash
- ADFS floppy access on the 82C711, including `ADFS_DiscOp` writes
- HostFS from Arculator's support ROM (extension ROM loading)
- RISC OS 3.11's CMOS defaults
- Blaston (1991) boots from its floppy image and runs, with no ADFFS
- SharedCLibrary 4.79 with RISC_OSLib inside it, the C parts compiled with GCC. A test program passes every check
- Battle Chess (1992) runs on that library

### Not yet

- DOSFS is in the ROM but hasn't read a DOS disc yet
- Alarm (its machine code helper is assembled by a BASIC program, and the image has no room left for it)
- Configure's settings that live in a boot application on disc, which are the desktop font, the RAM disc and the background texture
- Tactic doesn't start. It restores its saved configuration from the wrong disc data
- Palette utility on the icon bar
- Printing modules, Econet and NetFS
- Power-on self test
- Hard disc access is untested
- Sound hasn't been listened to
- Copy-protected floppy images (they need a track-level image format)
- Most games are untried
- Other emulators and real hardware are untried

The image uses 2,090,888 of the 2MB (2,097,152 bytes), and A5000 hardware and Arculator both stop at 2MB.

## Install

1. Download `ROM311` from the [latest release](../../releases/latest), or build it as [Building the ROM](#building-the-rom) describes.
2. In Arculator's folder, open `roms/riscos311`, which is where Arculator looks for its RISC OS 3.11 ROM, and move the files in it somewhere else, since Arculator loads every file in that folder, in name order, as one ROM.
3. Copy `ROM311` into `roms/riscos311`.
4. Set up an A5000 with RISC OS 3.11 as its ROM (that's Arculator's name for the slot ROO311 now fills), and start it.

| Machine | Notes |
| --- | --- |
| A5000 (ARM3, MEMC1a, 82C711 floppy controller, 4MB) | The machine it's built for and tested on. |
| Other Archimedes models | Untried. |

With an empty CMOS RAM the machine has no filing system configured, so hold Delete as it starts to set RISC OS 3.11's defaults, and it'll then start in the desktop.

## Using it

The machine starts in the desktop, where the Apps icon on the icon bar opens the applications in the ROM and the cog is the Task Manager.

| Key | Action |
| --- | --- |
| Delete, held as the machine starts | Set the CMOS RAM to RISC OS 3.11's defaults |
| Shift, held as the machine starts | Boot the floppy disc in drive 0 |
| F12 | Open a command line at the foot of the desktop. Return on an empty line closes it |
| Ctrl+Break | Reset the machine |

Configure sets the machine up, and its Screen window has menus for the monitor type, the colours and the resolution. **Set** changes the screen straight away and keeps the choice for the next start, and **Cancel** puts back what was there.

Files reach the machine on a floppy image or through HostFS, which Arculator's support ROM provides.

## How it works

The kernel and most modules are the RISC OS 3.60 sources, the oldest RISC OS Open publishes, and `Sources/UPSTREAM` records the repository and commit behind each folder. The kernel's MEMC1 build path hadn't been assembled since RISC OS 3.5, and it now assembles and runs again, with `git log -- Sources/Kernel` listing each repair. Changes to imported sources carry a comment starting `ROO311:` that says what changed.

The components listed in `Sources/NEWER` come from the current RISC OS Open sources and build against current headers (`Sources/Headers5`). FPEmulator is one of them, and the Desktop module is another, for its start-up banner, which reads RISC OS and not RISC OS 5. The cog on the icon bar is the current one too (`Sources/Desktop/Wimp5`), put into the same sprite form as the rest of the ROM's icons. It shows its 8 colours in a 256 colour mode, and in a 16 colour mode its purple and pink teeth are grey, the nearest the desktop's palette has.

The assembler sources were written for Acorn's AAsm and ObjAsm and are assembled with AsAsm. The C parts were written for the Norcroft compiler and are compiled with GCC 4.7.4, the last GCC that can target an ARM2 or ARM3, and they're the SharedCLibrary with RISC_OSLib inside it, Edit, Draw, Paint, Configure, Filer_Action, Squash and DOSFS. Each application is a module in the ROM that calls the library in the ROM directly, the way RISC OS 3 held Edit, Draw and Paint. [toolchain/README.md](toolchain/README.md) has the compiler options, the changes the sources needed and the 2 compiler faults that had to be fixed.

Fitting in 2MB takes the same methods the original build used. The message files are tokenized against the kernel's dictionary and Help's tokens, and Chars and Help, which are BASIC programs, go through BASIC's `CRUNCH` and the build's Squish tool, both ported to Python here. Together that frees 59K, which is what makes room for Configure. ColourTrans's ready-made tables for plotting 16 and 32 bit per pixel sprites are left out (83K), and it builds a table the first time one is wanted. SpriteExtend is built with its all-assembler code generator and no JPEG, as RISC OS 3.11's was. The ROM has a single set of icons, the high resolution one, and in a mode whose pixels aren't square (mode 12 on a TV-standard monitor) the Window Manager scales them.

Configure is the RISC OS 3.6 one, which was a disc application started by a boot application on disc. In the ROM it starts without the boot application, and what it kept in the CMOS RAM works. Its Screen window also keeps the monitor type and the desktop's mode in the CMOS RAM, as RISC OS 3.11 did (`*Configure MonitorType` and `WimpMode`), and its menus of colours and resolutions offer the numbered modes the chosen monitor can show, where before they came from the monitor definition files of later machines. What it kept in files of the boot application has nowhere to go yet.

The calculator is SciCalc, the one RISC OS Open publishes. It was a disc application that needed BASIC64, and in the ROM it runs on the ROM's BASIC, to 9 figures, unless BASIC64 has been loaded.

On an IOC machine a CMOS reset gives the RISC OS 3.11 settings for how the machine starts (drive 0, NoBoot, mouse step 3) and RISC OS Open's for how the desktop looks. The Podule manager is set up for 4 podules and extension ROMs, ADFS leaves out big disc support where the ST506 driver is present, and SoundDMA only has the 8-bit SWIs.

The kernel's workspace layout below `&1000` and in the VDU driver follows the RISC OS 3.60 sources, which moved some VDU variables compared to RISC OS 3.11, so software that reads those by address and not through `OS_ReadVduVariables` will see different values.

## Building the ROM

The build runs on Linux and needs AsAsm from GCCSDK (`svn://svn.riscos.info/gccsdk/trunk/tools/asasm`), `binutils-arm-none-eabi` and Python 3, and the C parts need GCC 4.7.4 for RISC OS. [toolchain/README.md](toolchain/README.md) says how to build both and what each one needs.

```bash
ASASM=/path/to/asasm GCC=/path/to/arm-unknown-riscos-gcc sh build.sh
```

The ROM is written to `build/A5000/rom`, and each module's ELF file beside it holds source line numbers. The same sources always give the same image, so it doesn't matter where or when it's built.

GitHub Actions runs this build from source on every push, compiler included (`.github/workflows/build.yml`), and a version tag publishes the image as `ROM311` in a release.

| File | What it does |
| --- | --- |
| `build.sh` | Assembles the kernel and modules, gathers resources, joins the ROM |
| `Sources/MODULES` | The modules after the kernel, in ROM order |
| `tools/mkres.py` | Gathers each component's messages, templates and sprites into the Messages module |
| `tools/mkrom.py` | Joins the kernel and modules into the image, and says what address a module will get |
| `tools/clib.ld`, `tools/romapp.ld`, `tools/app.ld` | Linker scripts for the SharedCLibrary module, a C program in the ROM and a C application on disc |
| `tests/clibtest.c` | A test of the SharedCLibrary (`sh build.sh clibtest`) |
| `tools/prepare.py`, `tools/tokhelp.py` | Make the source files the original build generated under RISC OS |
| `tools/fixcase.py` | Normalizes imported sources for AsAsm on Linux (file name case, backslashes) |
| `tools/romdiff.py` | Lines a built image up against a reference ROM and shows the code that differs |
| `tools/whereis.py` | Names the module and source line behind a ROM address |
| `tools/msgtok.py` | Tokenizes the ROM's message files, as the original build's MsgTok tools did |
| `tools/basic.py` | Lists a tokenized BBC BASIC file, crunches one as BASIC's `CRUNCH` does and squishes one as the build's Squish tool does |
| `tools/sprites.py` | Makes the ROM's sprite file from the sources' sprite files |

## AI use disclosure

ROO311 was built using [Claude Code](https://claude.com/claude-code) with Claude Fable 5.2.

## Credits

RISC OS was written by Acorn Computers. The sources ROO311 is built from are published by [RISC OS Open](https://www.riscosopen.org), and the cog on the icon bar and the start-up banner are theirs too.

The ROM is assembled with AsAsm and compiled with GCC 4.7.4 for RISC OS, both from [GCCSDK](https://www.riscos.info/index.php/GCCSDK), and it's tested in [Arculator](https://github.com/sarah-walker-pcem/arculator) by Sarah Walker.

The icon is the cog from the ROM's own icon bar.

## Licence

ROO311 is free software under the [Apache License, version 2.0](LICENSE). That covers the build scripts, tools and tests written for this project, and the RISC OS sources in `Sources/` are under it too. Each component carries its own `LICENSE` file, and 3 of them name other terms for some of their files (the New BSD licence and those of the Independent JPEG Group). The changes made to the sources here are under the same licences.
