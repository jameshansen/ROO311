## Install

Download `ROM311` below, then:

- **Arculator:** in Arculator's folder, move the files in `roms/riscos311` somewhere else, since Arculator loads every file there as one ROM, and copy `ROM311` in. Set up an A5000 with RISC OS 3.11 as its ROM and start it.
- **ArcEm:** start it with `--rom ROM311`, or name the file `ROM` in the folder ArcEm runs from.

Hold Delete the first time the machine starts. That sets RISC OS 3.11's default settings, and the machine then starts in the desktop.

`toolbox.zip` is the support pack, for programs that need the nested Window Manager or the Toolbox. Put `extrom.WindowManager` in the emulator's extension ROM (ArcEm's `extnrom` folder), and boot `!System` and `!Scrap` before running the program. The README's Support pack section has the details.
