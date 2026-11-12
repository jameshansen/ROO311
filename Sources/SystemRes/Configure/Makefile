# Copyright 1996 Acorn Computers Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Makefile for Configure
#
# ***********************************
# ***    C h a n g e   L i s t    ***
# ***********************************
# Date       Name    Description
# ----       ----    -----------
# 02-Nov-94  AMcC    Updated for Black build
# 30-Jan-95  AMcC    Configure/FontMerge now have separate installation
#

#
# Program specific options:
#
#COMPONENT  = Set in Components/Installation file
RDIR       = Resources
LDIR       = ${RDIR}.${LOCALE}

#
# Generic options:
#
MKDIR   = cdir
AS      = objasm
CC      = cc #-DTRACE=1
CP      = copy
LD      = link
RM      = remove
SQUEEZE = squeeze
WIPE    = -wipe

AFLAGS   = ${THROWBACK} -depend !Depend -nocache -stamp -quit
CFLAGS   = ${THROWBACK} -depend !Depend -ffah ${INCLUDES} ${DFLAGS}
DFLAGS   = -DBLUEROM -DSTANDALONE
INCLUDES = -IC:
CPFLAGS  = ~cfr~v
WFLAGS   = ~cr~v

#
# Libraries
#
CLIB      = CLib:o.stubs
RLIB      = RISC_OSLib:o.risc_oslib

# Configure
FILES =\
 ${RDIR}.!Boot\
 ${LDIR}.!Help\
 ${LDIR}.!Run\
 ${LDIR}.Messages\
 ${RDIR}.Sprites\
 ${RDIR}.Sprites22\
 ${LDIR}.Templates\
 ${RDIR}.tile_1\
 abs.!RunImage

# FontMerge
FONTFILES =\
 ${RDIR}.FontMerge.!Run\
 ${LDIR}.FontMerge.Messages\
 abs.FontMerge

OBJS =\
 o.apps\
 o.cmos\
 o.configfile\
 o.configure\
 o.econet\
 o.filer\
 o.floppies\
 o.fonts\
 o.harddiscs\
 o.keyboard\
 o.lock\
 o.memory\
 o.mouse\
 o.printer\
 o.screen\
 o.sound\
 o.system\
 o.version\
 o.wimpflags #o.ftrace

ASMS =\
 s.apps\
 s.cmos\
 s.configfile\
 s.configure\
 s.econet\
 s.filer\
 s.floppies\
 s.fonts\
 s.harddiscs\
 s.keyboard\
 s.lock\
 s.memory\
 s.mouse\
 s.printer\
 s.screen\
 s.sound\
 s.system\
 s.version\
 s.wimpflags

#
# Rule patterns
#
.SUFFIXES: .c .o .s .asm
.c.o:;     ${CC} -c ${CFLAGS} $<
.asm.o:;   ${AS} ${AFLAGS} $< $@
.c.s:;     ${CC} -s ${CFLAGS} $<

#
# Main rules:
#
all: ${FONTFILES} ${FILES}
	@echo ${COMPONENT}: Application built (Disc)

install: install_${COMPONENT}; @

install_Configure: ${FILES}
	|
	${MKDIR} ${INSTDIR}.!Configure
	|
	${CP} ${RDIR}.!Boot      ${INSTDIR}.!Configure.!Boot      ${CPFLAGS}
	${CP} ${LDIR}.!Help      ${INSTDIR}.!Configure.!Help      ${CPFLAGS}
	${CP} ${LDIR}.!Run       ${INSTDIR}.!Configure.!Run       ${CPFLAGS}
	${CP} abs.!RunImage      ${INSTDIR}.!Configure.!RunImage  ${CPFLAGS}
	${CP} ${LDIR}.Messages   ${INSTDIR}.!Configure.Messages   ${CPFLAGS}
	${CP} ${RDIR}.Sprites    ${INSTDIR}.!Configure.Sprites    ${CPFLAGS}
	${CP} ${RDIR}.Sprites22  ${INSTDIR}.!Configure.Sprites22  ${CPFLAGS}
	${CP} ${LDIR}.Templates  ${INSTDIR}.!Configure.Templates  ${CPFLAGS}
	${CP} ${RDIR}.tile_1     ${INSTDIR}.!Configure.tile_1     ${CPFLAGS}
	|
	Access ${INSTDIR}.!Configure /r
	Access ${INSTDIR}.!Configure.* WR/r
	|
	@echo Configure: Application installed (Disc)

install_FontMerge: ${FONTFILES}
	|
	${MKDIR} ${INSTDIR}.FontMerge
	|
	${CP} ${RDIR}.FontMerge.!Run      ${INSTDIR}.FontMerge.!Run      ${CPFLAGS}
	${CP} abs.FontMerge               ${INSTDIR}.FontMerge.FontMerge ${CPFLAGS}
	${CP} ${LDIR}.FontMerge.Messages  ${INSTDIR}.FontMerge.Messages  ${CPFLAGS}
	|
	Access ${INSTDIR}.FontMerge /r
	Access ${INSTDIR}.FontMerge.* WR/r
	|
	@echo FontMerge: Application installed (Disc)

# ROO26: Configure is held in the ROM with the other applications. Its program is a module (!Configure),
# which registers the sprites; these go into the Messages module.
RESDIR = <resource$dir>.Resources.Configure
RESAPP = <resource$dir>.Apps.!Configure
resources:
	${CP} ${RDIR}.ROM.!Boot ${RESAPP}.!Boot ${CPFLAGS}
	${CP} ${LDIR}.!Help     ${RESAPP}.!Help ${CPFLAGS}
	${CP} ${RDIR}.ROM.!Run  ${RESAPP}.!Run  ${CPFLAGS}
	${CP} ${LDIR}.Messages  ${RESDIR}.Messages ${CPFLAGS}
	${CP} ${LDIR}.Templates ${RESDIR}.Templates ${CPFLAGS}

clean:
	${WIPE} o.* ${WFLAGS}
	${RM} abs.!RunImage
	${RM} abs.FontMerge
	${WIPE} Test.Configure.* ${WFLAGS}
	${WIPE} Test.FontMerge ${WFLAGS}
	@echo ${COMPONENT}: cleaned

clean_all:
	-Destroy ${OBJS} abs.!RunImage ${INSTDIR}.!Configure.!Boot \
         ${INSTDIR}.!Configure.!Help ${INSTDIR}.!Configure.!Run \
         ${INSTDIR}.!Configure.!RunImage ${INSTDIR}.!Configure.Messages \
         ${INSTDIR}.!Configure.Sprites ${INSTDIR}.!Configure.Sprites22 \
         ${INSTDIR}.!Configure.Templates \
         ${INSTDIR}.!Configure.tile_1

asms: ${ASMS}

#
# Static dependencies:
#
abs.!RunImage: ${OBJS} ${RLIB} ${CLIB}
	${LD} -o $@ ${OBJS} ${RLIB} ${CLIB}
	${SQUEEZE} $@

abs.FontMerge: o.FontMerge ${CLIB}
	${LD} -o $@ o.FontMerge ${CLIB}
	${SQUEEZE} $@

#---------------------------------------------------------------------------
# Dynamic dependencies:
