#!/bin/sh
# Build ROO26 on Linux with open tools: AsAsm (GCCSDK) and GNU binutils for ARM.
# usage: sh build.sh [rom | kernel | modules | module <folder> <source> <name>]
#   ASASM    path to the asasm binary (default: asasm on PATH)
#   MACHINE  machine header to build for (default: A5000)
set -e
cd "$(dirname "$0")"
ROOT=$PWD
ASASM=${ASASM:-asasm}
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
	@*) "${2#@}" "$3" > "$B/$3.log" 2>&1 && link "$3" ;;
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
		-PreDefine='FileExt SETS ""' -PreDefine='FPEAnchorType SETS "Low"' -I.. -o "$B/$1.o" s/Archimedes
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
