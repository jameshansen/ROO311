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

# One folder of headers, as the export phase of a RISC OS build makes
rm -rf "$ROOT/build/Hdr"
mkdir -p "$ROOT/build/Hdr"
find Sources -type d -iname hdr | while read d; do cp -r "$d"/* "$ROOT/build/Hdr/"; done

# AsAsm reads RISC OS path and system variables from the environment in upper case
export HDR_PATH="$ROOT/build/Hdr" MACHINE IMAGESIZE LOCALE=${LOCALE:-UK} SYSTEM=${SYSTEM:-Ursula}

kernel() {
	cd "$ROOT/Sources/Kernel"
	"$ASASM" -ABSolute -Uppercase -NOWarn -G -o "$B/Kernel.o" s/GetAll
	arm-none-eabi-ld -Ttext=0x03800000 -e 0x03800000 -o "$B/Kernel.elf" "$B/Kernel.o"
	arm-none-eabi-objcopy -O binary "$B/Kernel.elf" "$B/Kernel"
	# Disassembly with the source line of each instruction, for finding an address from a line and back
	arm-none-eabi-objdump -dl -Mreg-names-raw "$B/Kernel.elf" | sed "s|$ROOT/||" > "$B/Kernel.lst"
	echo "Kernel: $(wc -c < "$B/Kernel") bytes"
}

# module <folder under Sources> <source file> <module name>: assemble one module to $B/<name>
module() {
	python3 "$ROOT/tools/tokhelp.py" "$ROOT/Sources/$1" > /dev/null
	cd "$ROOT/Sources/$1"
	"$ASASM" -ABSolute -Uppercase -NOWarn -G -o "$B/$3.o" "$2" > "$B/$3.log" 2>&1 &&
	arm-none-eabi-ld -Ttext=0 -e 0 -o "$B/$3.elf" "$B/$3.o" >> "$B/$3.log" 2>&1 &&
	arm-none-eabi-objcopy -O binary "$B/$3.elf" "$B/$3"
}

# the resource files of the kernel and every module, as the data block the Messages module registers
resdata() {
	cd "$ROOT"
	python3 tools/mkres.py "$B/resdata" "$LOCALE" Sources/Kernel $(grep -v '^[#-]' Sources/MODULES | awk 'NF==3{print "Sources/"$1}')
}

# every module in Sources/MODULES; reports the ones that fail and carries on
modules() {
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
