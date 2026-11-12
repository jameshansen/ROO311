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
# Makefile for SciCalc
#
# ***********************************
# ***    C h a n g e   L i s t    ***
# ***********************************
# Date       Name   Description
# ----       ----   -----------
# 05-Nov-94  AMcC   Updated for Black build
#

#
# Program specific options:
#
COMPONENT  = SciCalc
APP        = !${COMPONENT}
RDIR       = Resources
LDIR       = ${RDIR}.${LOCALE}
INSTDIR    = ${INSTDIR}.${APP}

#
# Generic options:
#
MKDIR   = cdir
CP      = copy
RM      = remove
SQUISH  = squish
WIPE    = -wipe

CPFLAGS = ~cfr~v
SQFLAGS = -nolist
WFLAGS  = ~c~v

FILES =\
 $(LDIR).!Help\
 $(LDIR).!Run\
 $(RDIR).!RunImage\
 $(LDIR).!Sprites\
 $(LDIR).Messages\
 $(LDIR).Sprites\
 $(LDIR).Templates

#
# Main rules:
#
all: ${FILES}
	@echo ${COMPONENT}: Application built (Disc}

install: ${FILES}
	${MKDIR} ${INSTDIR}
	${CP} ${LDIR}.!Help      ${INSTDIR}.!Help     ${CPFLAGS}
	${CP} ${LDIR}.!Run       ${INSTDIR}.!Run      ${CPFLAGS}
	${CP} ${RDIR}.!RunImage  ${INSTDIR}.!RunImage ${CPFLAGS}
	${CP} ${LDIR}.!Sprites   ${INSTDIR}.!Sprites  ${CPFLAGS}
	${CP} ${LDIR}.Messages   ${INSTDIR}.Messages  ${CPFLAGS}
	${CP} ${LDIR}.Sprites    ${INSTDIR}.Sprites   ${CPFLAGS}
	${CP} ${LDIR}.Templates  ${INSTDIR}.Templates ${CPFLAGS}
	Access ${INSTDIR} /r
	Access ${INSTDIR}.* lr/r
	@echo ${COMPONENT}: Application installed {Disc}

# ROO311: SciCalc was a disc application only. This rule puts it in the ROM's Apps folder, with a !Run
# that does without BASIC64 (Resources.UK.ROM.!Run).
RESAPP = <resource$dir>.Apps.${APP}

resources:
	${MKDIR} ${RESAPP}
	${CP} ${LDIR}.!Help      ${RESAPP}.!Help     ${CPFLAGS}
	${CP} ${LDIR}.ROM.!Run   ${RESAPP}.!Run      ${CPFLAGS}
	${CP} ${RDIR}.!RunImage  ${RESAPP}.!RunImage ${CPFLAGS}
	${CP} ${LDIR}.!Sprites   ${RESAPP}.!Sprites  ${CPFLAGS}
	${CP} ${LDIR}.Messages   ${RESAPP}.Messages  ${CPFLAGS}
	${CP} ${LDIR}.Sprites    ${RESAPP}.Sprites   ${CPFLAGS}
	${CP} ${LDIR}.Templates  ${RESAPP}.Templates ${CPFLAGS}
	@echo ${COMPONENT}: resource files copied

clean:
	${RM} ${RDIR}.!RunImage
	${WIPE} crunched.* ${WFLAGS}
	@echo ${COMPONENT}: cleaned

#
# Static dependencies:
#
${RDIR}.!RunImage: crunched.!RunImage
	${SQUISH} ${SQFLAGS} -from crunched.!RunImage -to $@

crunched.!RunImage: bas.!RunImage
	crunch.!RunImage; BASIC

#---------------------------------------------------------------------------
# Dynamic dependencies:
