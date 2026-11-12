#!/bin/sh
# Build ROO26 on Linux with open tools: AsAsm (GCCSDK) and GNU binutils for ARM.
# usage: sh build.sh [rom | kernel | modules | module <folder> <source> <name>]
#   ASASM    path to the asasm binary (default: asasm on PATH)
#   GCC      path to GCC 4.7.4 for RISC OS, for the C parts (default: arm-unknown-riscos-gcc on PATH)
#   MACHINE  machine header to build for (default: A5000)
set -e
cd "$(dirname "$0")"
ROOT=$PWD
ASASM=${ASASM:-asasm}
GCC=${GCC:-arm-unknown-riscos-gcc}
MACHINE=${MACHINE:-A5000}
IMAGESIZE=${IMAGESIZE:-2048K}
B=$ROOT/build/$MACHINE
mkdir -p "$B"

# Two folders of headers, as the export phase of a RISC OS build makes one.
#   Hdr   for the kernel and the components taken from the RISC OS 3.60 sources
#   Hdr5  for components taken from the current RISC OS Open sources: current HdrSrc and kernel headers
#         (Sources/Headers5) plus those components' own. They build for the machine "Archimedes", which the
#         current headers define as a 26-bit only machine.
# Sources/NEWER lists the components that use Hdr5. Their own headers go into Hdr as well, since the older
# components include them (the Window Manager wants Hdr:FPEmulator).
rm -rf "$ROOT/build/Hdr" "$ROOT/build/Hdr5"
mkdir -p "$ROOT/build/Hdr" "$ROOT/build/Hdr5"
NEWER=$(grep -v '^#' Sources/NEWER | sed 's|^|Sources/|')
find Sources -type d -iname hdr | while read d; do
	case "$d" in Sources/Headers5/*) cp -r "$d"/* "$ROOT/build/Hdr5/"; continue ;; esac
	cp -r "$d"/* "$ROOT/build/Hdr/"
	for n in $NEWER; do case "$d" in "$n"/*) cp -r "$d"/* "$ROOT/build/Hdr5/" ;; esac; done
done
# Hdr5 then takes what it still lacks from Hdr: the headers of the components that are only in the 3.60
# sources (the Window Manager's, the Font Manager's), which a newer component can need too.
cp -rn "$ROOT/build/Hdr/." "$ROOT/build/Hdr5/"

# AsAsm reads RISC OS path and system variables from the environment in upper case
export ASASM HDR_PATH="$ROOT/build/Hdr" MACHINE IMAGESIZE LOCALE=${LOCALE:-UK} SYSTEM=${SYSTEM:-Ursula}

kernel() {
	cd "$ROOT/Sources/Kernel"
	"$ASASM" -ABSolute -Uppercase -NOWarn -G -o "$B/Kernel.o" s/GetAll
	arm-none-eabi-ld -Ttext=0x03800000 -e 0x03800000 -o "$B/Kernel.elf" "$B/Kernel.o"
	arm-none-eabi-objcopy -O binary "$B/Kernel.elf" "$B/Kernel"
	# Disassembly with the source line of each instruction, for finding an address from a line and back
	arm-none-eabi-objdump -dl -Mreg-names-raw "$B/Kernel.elf" | sed "s|$ROOT/||" > "$B/Kernel.lst"
	echo "Kernel: $(wc -c < "$B/Kernel") bytes"
}

# link <name>: $B/<name>.o to the module file $B/<name>
link() {
	arm-none-eabi-ld -Ttext=0 -e 0 -o "$B/$1.elf" "$B/$1.o" >> "$B/$1.log" 2>&1 &&
	arm-none-eabi-objcopy -O binary "$B/$1.elf" "$B/$1"
}

# module <folder under Sources> <source file> <module name>: assemble one module to $B/<name>.
# A source of the form @name runs the function of that name below instead, for a module with a build of its own.
module() {
	python3 "$ROOT/tools/tokhelp.py" "$ROOT/Sources/$1" > /dev/null
	python3 "$ROOT/tools/prepare.py" "$ROOT/Sources/$1"
	cd "$ROOT/Sources/$1"
	case "$2" in
	@*) "${2#@}" "$3" > "$B/$3.log" 2>&1 ;;
	*) "$ASASM" -ABSolute -Uppercase -NOWarn -G -o "$B/$3.o" "$2" > "$B/$3.log" 2>&1 && link "$3" ;;
	esac
}

# newer <asasm arguments>: assemble an ObjAsm-format source from the current RISC OS Open tree, 26-bit
newer() {
	HDR_PATH="$ROOT/build/Hdr5" MACHINE=Archimedes "$ASASM" -NOWarn -G -apcs 3/26bit "$@"
}

# The floating point emulator, with FPA hardware support, as its Makefile builds it for RISC OS 3.1
fpemulator() {
	newer -PreDefine='CoreDir SETS "../coresrc/s/"' -PreDefine='VeneerDir SETS "../vensrc/riscos/"' \
		-PreDefine='FileExt SETS ""' -PreDefine='FPEAnchorType SETS "Low"' -I.. -o "$B/$1.o" s/Archimedes && link "$1"
}

# The Desktop module of the current RISC OS Open sources, which shows their start-up banner. The banner
# and the options it is built with are those of the "Sovereign" user interface.
desktop5() {
	USERIF=Sovereign newer -o "$B/$1.o" s/Desktop && link "$1"
}

# romaddr <name>: the address module <name> gets in the ROM, from the kernel and the modules ahead of it
romaddr() {
	python3 "$ROOT/tools/mkrom.py" --next "$B/Kernel" $(grep -v '^[#-]' "$ROOT/Sources/MODULES" | while read dir src name; do
		[ "$name" = "$1" ] && break
		[ -f "$B/$name" ] && echo "$B/$name"
	done)
}

# modcc <offset> <object> <source> <gcc arguments>: compile one C source to run inside a module.
# GCC's module code reaches a static variable as a constant plus a relocation offset. Two things in the
# compiler's assembler output are changed before it is assembled:
#   - the offset GCC loads is the client's, the word at sl-536. <offset> is 536 to keep that, or 540 for
#     code in the shared library, which has to use the library's offset, the word below.
#   - the constant is written sym(GOTOFF), which only GCCSDK's linker in its module mode resolves to the
#     address of sym. Written plain, any linker does.
# toolchain/README.md has the rest of the options.
# C_DIALECT makes GCC read C the way the Norcroft compiler these sources were written for did.
C_DIALECT="-funsigned-bitfields -fno-strict-aliasing -fwrapv -fno-delete-null-pointer-checks"
modcc() {
	off=$1 out=$2 src=$3; shift 3
	"$GCC" -mmodule -ffixed-sl -mno-poke-function-name -fno-section-anchors -ffreestanding -fno-common -Os \
		-nostdinc $C_DIALECT -D__arm -D___type= "$@" -x c -S -o "${out%.o}.s" "$src" &&
	sed -i -e "s/\[sl, #-536\]/[sl, #-$off]/" -e 's/(GOTOFF)$//' "${out%.o}.s" &&
	"$GCC" -mmodule -c -o "$out" "${out%.o}.s"
}
libcc() { modcc 540 "$@"; }

# The SharedCLibrary, with RISC_OSLib inside it for the ROM's own C programs, as the RISC OS 3 ROM had it.
# C code holds absolute addresses, so the module is linked for its place in the ROM.
clib() {
	O="$B/clib"; rm -rf "$O"; mkdir -p "$O/inc" "$O/c" "$O/r"
	# the headers, under the names the sources include them by: <name.h>, "h.name" and "h.Folder.name"
	for h in h/* clib/h/* rlib/h/*; do
		[ -f "$h" ] && ln -s "$PWD/$h" "$O/inc/${h##*/}.h" && ln -s "$PWD/$h" "$O/inc/h.${h##*/}"
	done
	for h in rlib/h/*/*; do
		d=${h%/*}; d=${d##*/}
		# the folder is spelt three ways: EditIntern, editintern, Editintern
		for v in "$d" "$(echo "$d" | tr A-Z a-z)" "${d%Intern}intern"; do ln -sf "$PWD/$h" "$O/inc/h.$v.${h##*/}"; done
	done
	# swis.h is what an assembly of s.makehswis puts out
	"$ASASM" -ABSolute -Uppercase -NOWarn -o "$O/swis.elf" s/makehswis &&
	arm-none-eabi-objcopy -O binary "$O/swis.elf" "$O/swis.bin" && tr -d '\0' < "$O/swis.bin" > "$O/inc/swis.h" &&
	ln -s swis.h "$O/inc/h.swis" || return 1
	for s in clib/s/cl_rmhdr rlib/s/initmod_r kernel/s/k_mod_r clib/s/cl_mod_r s/memcpy kernel/s/swiv \
		rlib/s/rl_mod_r rlib/s/bastxt rlib/s/poll rlib/s/swi; do
		"$ASASM" -Uppercase -NOWarn -G -apcs 3/26bit -o "$O/${s##*/}.o" "$s" || return 1
	done
	fail=
	for c in alloc armsys ctype error fpprintf locale math printf scanf signal sort stdio stdlib string time; do
		case $c in
		# no stack limit checks where the sources turn them off (#pragma -s1): the storage allocator, which
		# the stack extension code calls, and the signal code, which runs when the stack has overflowed
		alloc | signal) chk= ;;
		*) chk=-mapcs-stack-check ;;
		esac
		libcc "$O/c/$c.o" c/$c $chk -I"$O/inc" -DSHARED_C_LIBRARY -DUROM -DDDE -DSEPERATE_MEMCPY \
			'-DLIB_SHARED="Shared "' '-DLIB_APCS="R"' || fail="$fail $c"
	done
	for c in akbd alarm baricon bbc colourmenu colourtran dbox dboxfile dboxquery dboxtcol dragasprit drawmod \
		event fileicon flex font heap help magnify menu msgs os pointer print res resspr saveas sprite template \
		txt txt1 txt3 txtar txtedit txtfile txtfind txtmisc txtopt txtoptmenu txtregexp txtscrap txtundo txtwin \
		visdelay werr wimp wimpt win xferrecv xfersend; do
		libcc "$O/r/$c.o" rlib/c/$c -mapcs-stack-check -I"$O/inc" -DSHARED_C_LIBRARY -DUROM -DDDE \
			-DFIELDNUM -DBIG_WINDOWS -DSETOPTIONS -DALLOW_OLD_PATTERNS -DSET_MISC_OPTIONS || fail="$fail $c"
	done
	[ -z "$fail" ] || { echo "did not compile:$fail"; return 1; }
	# the room the stubs hold for each library's statics: its exported variables and the space that
	# clib.s.clibdata and rlib.s.rlibdata name
	datasize() {
		echo $(($(arm-none-eabi-size -A "$O/$1.o" | awk '$1 == "C$$data" { print $2 }') + $(awk '/Space +Variable/ { print $3 * 4 }' "$2")))
	}
	"$("$GCC" -print-prog-name=ld)" -T "$ROOT/tools/clib.ld" --defsym ROMADDR="$(romaddr "$1")" \
		--defsym CLSIZE="$(datasize cl_mod_r clib/s/clibdata)" --defsym RLSIZE="$(datasize rl_mod_r rlib/s/rlibdata)" \
		-Map "$B/$1.map" -o "$B/$1.elf" "$O"/*.o "$O"/c/*.o "$O"/r/*.o "$("$GCC" -mmodule -print-libgcc-file-name)" &&
	arm-none-eabi-objcopy -O binary "$B/$1.elf" "$B/$1" || return 1
	# For the C programs that follow in the ROM: the stubs they link with, and the address of everything the
	# library defines, which they call directly. PROVIDE gives way to a program's own symbol of the same name.
	# The area boundaries (Area$$Base, Area$$Limit) are left out: each program's link makes its own.
	"$ASASM" -Uppercase -NOWarn -apcs 3/26bit -o "$O/romstubs.obj" rlib/s/rl_stub_rm &&
	"$ASASM" -Uppercase -NOWarn -apcs 3/26bit -o "$O/romcstubs.obj" clib/s/cl_stub_rm &&
	arm-none-eabi-nm -g --defined-only "$B/$1.elf" | awk '$3 !~ /[$][$]/ { printf "PROVIDE(\"%s\" = 0x%s);\n", $3, $1 }' > "$O/abssym.ld"
}

# hdrlinks <include folder> <header>...: make each header includable as "name.h" and "h.name", as spelt,
# in lower case and in upper case. RISC OS does not mind which, and the sources use all three.
hdrlinks() {
	inc=$1; shift
	for h; do
		n=${h##*/}
		for v in "$n" "$(echo "$n" | tr A-Z a-z)" "$(echo "$n" | tr a-z A-Z)"; do
			ln -sf "$PWD/$h" "$inc/$v.h"; ln -sf "$PWD/$h" "$inc/h.$v"
		done
	done
	# and any other spelling the component's sources use for one of its own or the library's headers
	grep -ho '#include *"[^"]*"' c/* h/* 2>/dev/null | sed 's/.*"\(.*\)"/\1/' | sort -u | while read n; do
		[ -e "$inc/$n" ] || [ -e "$B/clib/inc/$n" ] && continue
		for d in "$inc" "$B/clib/inc"; do
			m=$(ls "$d" | grep -i -x -F "$n" | head -1)
			if [ -n "$m" ]; then ln -sf "$(readlink -f "$d/$m")" "$inc/$n"; break; fi
		done
	done
}

# romapp <name>: a C application held in the ROM as a module, the way RISC OS 3 held Edit, Draw and Paint.
# RISC_OSLib's module wrapper is its header, its C files are compiled as module code, and it calls the
# library in the ROM directly. It comes after the SharedCLibrary in Sources/MODULES, under the module's
# title (!Edit).
romapp() {
	asms= defs=
	case $1 in
	!Edit) srcs="edit editv message slist" ;;
	!Configure) srcs="Apps CMOS configfile Configure econet Filer Floppies Fonts HardDiscs Keyboard Lock Memory
		Mouse Printer Screen Sound System version WimpFlags"
		defs="-DBLUEROM -DSTANDALONE" ;;
	!Draw) srcs="Draw DrawAction DrawCheck DrawDispl DrawDXF DrawEdit DrawEnter DrawFileIO DrawGrid DrawHelp
		DrawMenu DrawObject DrawPrint DrawScan DrawSelect DrawTextC DrawTrans DrawUndo bezierarc"
		asms="asm/jpeg" ;;
	!Paint) srcs="Colours Main Menus PSprite SprWindow Tools ToolWindow"; asms="asm/jpeg asm/writepixel" ;;
	Filer_Action) srcs="actionwind Initialise Buttons memmanage listfiles Chains debug"; asms="s/allerrs" ;;
	esac
	O="$B/$1.d"; rm -rf "$O"; mkdir -p "$O/inc"
	hdrlinks "$O/inc" h/*
	"$ASASM" -Uppercase -NOWarn -G -apcs 3/26bit -o "$O/ModuleWrap.o" "$ROOT/Sources/Lib/RISC_OSLib/s/modulewrap" || return 1
	for s in $asms; do
		"$ASASM" -Uppercase -NOWarn -G -apcs 3/26bit -o "$O/${s##*/}.o" "$s" || return 1
	done
	for c in $srcs; do
		modcc 536 "$O/$c.o" c/$c -mapcs-stack-check -I"$O/inc" -I"$B/clib/inc" $defs || return 1
	done
	"$("$GCC" -print-prog-name=ld)" -T "$ROOT/tools/romapp.ld" -T "$B/clib/abssym.ld" --defsym ROMADDR="$(romaddr "$1")" \
		-Map "$B/$1.map" -o "$B/$1.elf" "$O"/*.o "$B/clib/romstubs.obj" "$("$GCC" -mmodule -print-libgcc-file-name)" &&
	arm-none-eabi-objcopy -O binary "$B/$1.elf" "$B/$1"
}

# The Squash module: C inside a module header of its own (s.mr_module), with no library. Its statics are
# found through the word sl points at, where the header keeps the relocation offset (hdr.magicoff), so that
# is the offset its C is compiled for.
squash() {
	O="$B/$1.d"; rm -rf "$O"; mkdir -p "$O/inc"
	hdrlinks "$O/inc" h/*
	for s in s/mr_module s/statics s/comp_ass s/debug s/zcat_ass12; do
		"$ASASM" -Uppercase -NOWarn -G -apcs 3/26bit -o "$O/${s##*/}.o" "$s" || return 1
	done
	for c in compress cssr trial zssr; do
		modcc 0 "$O/$c.o" c/$c -I"$O/inc" -I"$B/clib/inc" || return 1
	done
	"$("$GCC" -print-prog-name=ld)" -T "$ROOT/tools/romapp.ld" -T "$B/clib/abssym.ld" --defsym ROMADDR="$(romaddr "$1")" \
		-Map "$B/$1.map" -o "$B/$1.elf" "$O"/*.o "$("$GCC" -mmodule -print-libgcc-file-name)" &&
	arm-none-eabi-objcopy -O binary "$B/$1.elf" "$B/$1"
}

# DOSFS: a C module whose header is generated from a description (cmhg.DOSFShdr). CMunge, which the GCCSDK
# build installs beside the compiler, writes the header as assembler for 26-bit code. The module uses the
# C library only, through the ROM stubs.
dosfs() {
	O="$B/$1.d"; rm -rf "$O"; mkdir -p "$O/inc"
	hdrlinks "$O/inc" h/*
	# Of the C header CMunge writes, only the #define lines are kept, which is what the header generator of
	# the time gave. The rest declares the module's handlers with types the 1996 source does not match.
	"$(dirname "$(command -v "$GCC")")/cmunge" -tnorcroft -26bit -s "$O/hdr.s" -d "$O/cmunge.h" cmhg/DOSFShdr &&
	grep '^#' "$O/cmunge.h" > "$O/inc/DOSFShdr.h" && ln -s DOSFShdr.h "$O/inc/h.DOSFShdr" &&
	"$ASASM" -Uppercase -NOWarn -apcs 3/26bit -o "$O/DOSFShdr.o" "$O/hdr.s" || return 1
	# -apcs none, as its Makefile has it: s.DOSFSctl gives the names v1 to v5 to registers of its own choosing
	for s in s/DOSFSctl s/StaticDefs s/init; do
		"$ASASM" -Uppercase -NOWarn -G -apcs none -o "$O/${s##*/}.o" "$s" || return 1
	done
	for c in DOSFS DOSFSops DOSnaming FSerrors TIMEconv wcompare debug MsgTrans Statics; do
		modcc 536 "$O/$c.o" c/$c -I"$O/inc" -I"$B/clib/inc" || return 1
	done
	"$("$GCC" -print-prog-name=ld)" -T "$ROOT/tools/romapp.ld" -T "$B/clib/abssym.ld" --defsym ROMADDR="$(romaddr "$1")" \
		-Map "$B/$1.map" -o "$B/$1.elf" "$O"/*.o "$B/clib/romcstubs.obj" "$("$GCC" -mmodule -print-libgcc-file-name)" &&
	arm-none-eabi-objcopy -O binary "$B/$1.elf" "$B/$1"
}

# tests/clibtest.c as an application, linked with the library's stubs. Wants the headers clib() sets up.
clibtest() {
	cd "$ROOT/Sources/Lib/RISC_OSLib"
	"$ASASM" -Uppercase -NOWarn -apcs 3/26bit -o "$B/clib/stubs.obj" clib/s/cl_stub_r
	"$GCC" -mlibscl -mno-poke-function-name -fno-builtin -O2 -nostdinc -I"$B/clib/inc" -D__arm -D___type= \
		-c -o "$B/clibtest.o" "$ROOT/tests/clibtest.c"
	"$("$GCC" -print-prog-name=ld)" -T "$ROOT/tools/app.ld" -o "$B/clibtest.elf" "$B/clib/stubs.obj" "$B/clibtest.o" \
		"$("$GCC" -mlibscl -print-libgcc-file-name)"
	arm-none-eabi-objcopy -O binary "$B/clibtest.elf" "$B/clibtest,ff8"
}

# the resource files of the kernel and every module, as the data block the Messages module registers
resdata() {
	cd "$ROOT"
	python3 tools/mkres.py "$B/resdata" "$LOCALE" Sources/Kernel $(grep -v '^[#-]' Sources/MODULES | awk 'NF>=2{print "Sources/"$1}')
}

# every module in Sources/MODULES; reports the ones that fail and carries on
modules() {
	# generated files first: gathering the resources wants some of them
	grep -v '^[#-]' "$ROOT/Sources/MODULES" | while read dir src name; do
		if [ -n "$name" ]; then python3 "$ROOT/tools/prepare.py" "$ROOT/Sources/$dir"; fi
	done
	resdata
	export RESDATA="$B/resdata"
	grep -v '^[#-]' "$ROOT/Sources/MODULES" | while read dir src name; do
		[ -n "$name" ] || continue
		rm -f "$B/$name"
		if module "$dir" "$src" "$name"; then
			echo "$name: $(wc -c < "$B/$name") bytes"
		else
			echo "$name: FAILED, $(grep -c Error "$B/$name.log") errors, see $B/$name.log"
		fi
	done
}

# the ROM image: the kernel, then every module that built, in MODULES order
rom() {
	kernel
	modules
	cd "$ROOT"
	python3 tools/mkrom.py "$B/rom" "${IMAGESIZE%K}" "$B/Kernel" $(grep -v '^[#-]' Sources/MODULES | while read dir src name; do [ -f "$B/$name" ] && echo "$B/$name"; done)
}

"${1:-rom}" "$2" "$3" "$4"
