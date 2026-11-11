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
# Makefile for SCSIFS
#
# ***********************************
# ***    C h a n g e   L i s t    ***
# ***********************************
# Date       Name         Description
# ----       ----         -----------
# 25-May-94  AMcC         Created.
#

#
# Paths
#
EXP_HDR = <export$dir>

#
# Generic options:
#
MKDIR    = cdir
AS       = aasm
CP       = copy
RM       = remove
TOKENISE = tokenise

CFLAGS   = -c -depend !Depend -IC:
AFLAGS   = -depend !Depend -Stamp -quit -module
CPFLAGS  = ~cfr~v

TOKENS   = Hdr:Tokens

#
# Program specific options:
#
COMPONENT = SCSIFS
SOURCE    = s.Hdr_fst
TARGET    = rm.SCSIFS
EXPORTS   = ${EXP_HDR}.${COMPONENT}

#
# Generic rules:
#
all: ${TARGET}
	@echo ${COMPONENT}: all built

export: ${EXPORTS}
	@echo ${COMPONENT}: export complete

install: ${TARGET}
	${CP} ${TARGET} ${INSTDIR}.${COMPONENT} ${CPFLAGS}
	@echo ${COMPONENT}: installed

clean:
	${RM} ${TARGET}
	${RM} TokenHelp
	@echo ${COMPONENT}: cleaned

${TARGET}: ${SOURCE} TokenHelp
	${AS} ${AFLAGS} -To $@ -From ${SOURCE}

TokenHelp: ${TOKENS} HelpText
	${TOKENISE} ${TOKENS} HelpText $@

${EXP_HDR}.${COMPONENT}: hdr.${COMPONENT}
	${CP} hdr.${COMPONENT} $@ ${CPFLAGS}

# Dynamic dependencies:
