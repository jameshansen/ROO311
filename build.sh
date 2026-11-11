#!/bin/sh
# Build ROO26 on Linux with open tools: AsAsm (GCCSDK) and GNU binutils for ARM.
# usage: sh build.sh [kernel]
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
export HDR_PATH="$ROOT/build/Hdr" MACHINE IMAGESIZE

kernel() {
	cd "$ROOT/Sources/Kernel"
	"$ASASM" -ABSolute -Uppercase -NOWarn -o "$B/Kernel.o" s/GetAll
	arm-none-eabi-ld -Ttext=0x03800000 -e 0x03800000 -o "$B/Kernel.elf" "$B/Kernel.o"
	arm-none-eabi-objcopy -O binary "$B/Kernel.elf" "$B/Kernel"
	echo "Kernel: $(wc -c < "$B/Kernel") bytes"
}

"${1:-kernel}"
