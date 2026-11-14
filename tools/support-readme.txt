ROO311 support pack
===================

This is the support pack's !System.!Help.

Modules that RISC OS 3.11 didn't have, for the programs that need them, built from RISC OS Open's sources by ROO311's build (sh build.sh support).

extrom.WindowManager
  Window Manager 4.01 (30 Sep 1998), built for RISC OS 3.1: the nested Window Manager. It can't replace the Window Manager once the desktop has started, so it goes in an extension ROM, where its newer version takes the ROM's place at power on.

!System.Modules.CallASWI
  CallASWI 0.03, which gives RISC OS 3.1 the SWIs RISC OS 3.7 added: OS_CallASWI, OS_CallASWIR12, OS_PlatformFeatures and OS_SynchroniseCodeAreas.

!System.Modules.Toolbox
  The Toolbox: Toolbox 1.47, Window 1.61, Menu 0.34, Iconbar 1.18, ProgInfo 0.15, SaveAs 0.16, Scale 0.14 and DCS 1.08 (DCS_Quit).

!System, !Scrap
  Set System$Path and Wimp$ScrapDir when booted, as RISC OS 3's did.

The sources and the commit each came from are in ROO311's repository, under Support/. They are Acorn's, published by RISC OS Open under the Apache License, version 2.0, as is ROO311.
