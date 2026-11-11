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

# romaddr <name>: the address module <name> gets in the ROM, from the kernel and the modules ahead of it
romaddr() {
	python3 "$ROOT/tools/mkrom.py" --next "$B/Kernel" $(grep -v '^[#-]' "$ROOT/Sources/MODULES" | while read dir src name; do
		[ "$name" = "$1" ] && break
		[ -f "$B/$name" ] && echo "$B/$name"
	done)
}

# libcc <object> <source> <gcc arguments>: compile one C source of a shared library.
# GCC's module code reaches a static variable as a constant plus a relocation offset. Two things in the
# compiler's assembler output are changed before it is assembled:
#   - the offset is the client's, the word at sl-536. Code in the library has to use the library's, the
#     word below that.
#   - the constant is written sym(GOTOFF), which only GCCSDK's linker in its module mode resolves to the
#     address of sym. Written plain, any linker does.
# toolchain/README.md has the rest of the options.
# C_DIALECT makes GCC read C the way the Norcroft compiler these sources were written for did.
C_DIALECT="-funsigned-bitfields -fno-strict-aliasing -fwrapv -fno-delete-null-pointer-checks"
libcc() {
	out=$1 src=$2; shift 2
	"$GCC" -mmodule -mno-poke-function-name -fno-section-anchors -ffreestanding -fno-common -O2 -nostdinc \
		$C_DIALECT -D__arm -D___type= "$@" -x c -S -o "${out%.o}.s" "$src" &&
	sed -i -e 's/\[sl, #-536\]/[sl, #-540]/' -e 's/(GOTOFF)$//' "${out%.o}.s" &&
	"$GCC" -mmodule -c -o "$out" "${out%.o}.s"
}

# The SharedCLibrary. C code holds absolute addresses, so the module is linked for its place in the ROM.
clib() {
	O="$B/clib"; rm -rf "$O"; mkdir -p "$O/inc"
	# the headers, under both names the sources include them by: <name.h> and "h.name"
	for h in h/* clib/h/*; do
		[ -f "$h" ] && ln -s "$PWD/$h" "$O/inc/${h##*/}.h" && ln -s "$PWD/$h" "$O/inc/h.${h##*/}"
	done
	# swis.h is what an assembly of s.makehswis puts out
	"$ASASM" -ABSolute -Uppercase -NOWarn -o "$O/swis.elf" s/makehswis &&
	arm-none-eabi-objcopy -O binary "$O/swis.elf" "$O/swis.bin" && tr -d '\0' < "$O/swis.bin" > "$O/inc/swis.h" &&
	ln -s swis.h "$O/inc/h.swis" || return 1
	for s in clib/s/cl_rmhdr rlib/s/initmod_r kernel/s/k_mod_r clib/s/cl_mod_r s/memcpy kernel/s/swiv; do
		"$ASASM" -Uppercase -NOWarn -G -apcs 3/26bit -o "$O/${s##*/}.o" "$s" || return 1
	done
	for c in alloc armsys ctype error fpprintf locale math printf scanf signal sort stdio stdlib string time; do
		case $c in
		# no stack limit checks where the sources turn them off (#pragma -s1): the storage allocator, which
		# the stack extension code calls, and the signal code, which runs when the stack has overflowed
		alloc | signal) chk= ;;
		*) chk=-mapcs-stack-check ;;
		esac
		libcc "$O/$c.o" c/$c $chk -I"$O/inc" -DSHARED_C_LIBRARY -DUROM -DDDE -DSEPERATE_MEMCPY \
			'-DLIB_SHARED="Shared "' '-DLIB_APCS="R"' || return 1
	done
	# the stubs' room for the library's statics: its exported variables and the space clib.s.clibdata names
	clsize=$(($(arm-none-eabi-size -A "$O/cl_mod_r.o" | awk '$1 == "C$$data" { print $2 }') + $(awk '/^ClibSpace/ { print $3 * 4 }' clib/s/clibdata)))
	"$("$GCC" -print-prog-name=ld)" -T "$ROOT/tools/clib.ld" --defsym ROMADDR="$(romaddr "$1")" --defsym CLSIZE=$clsize \
		-Map "$B/$1.map" -o "$B/$1.elf" "$O"/*.o "$("$GCC" -mmodule -print-libgcc-file-name)" &&
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
	python3 tools/mkres.py "$B/resdata" "$LOCALE" Sources/Kernel $(grep -v '^[#-]' Sources/MODULES | awk 'NF==3{print "Sources/"$1}')
}

# every module in Sources/MODULES; reports the ones that fail and carries on
modules() {
	# generated files first: gathering the resources wants some of them
	grep -v '^[#-]' "$ROOT/Sources/MODULES" | while read dir src name; do
		[ -n "$name" ] && python3 "$ROOT/tools/prepare.py" "$ROOT/Sources/$dir"
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
