#!/bin/sh
# Fetch what the compiler build needs, into <work dir>: the GCCSDK build recipe at a fixed revision and the
# source archives it would otherwise download for itself. Every archive is checked against SHA256SUMS.
# usage: sh toolchain/fetch.sh <work dir>
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$1"
cd "$1"

GCCSDK_REVISION=7800
[ -d gcc4 ] || svn co -q -r $GCCSDK_REVISION svn://svn.riscos.info/gccsdk/trunk/gcc4 gcc4

mkdir -p gcc4/srcdir.orig
cd gcc4/srcdir.orig
get() { [ -f "$(basename "$1")" ] || wget -q --timeout=60 --tries=3 "$1"; }
get https://ftp.gnu.org/gnu/autoconf/autoconf-2.64.tar.bz2
get https://ftp.gnu.org/gnu/automake/automake-1.11.1.tar.bz2
get https://ftp.gnu.org/gnu/libtool/libtool-2.4.2.tar.gz
get https://ftp.gnu.org/gnu/binutils/binutils-2.24.tar.bz2
get https://ftp.gnu.org/gnu/gcc/gcc-4.7.4/gcc-4.7.4.tar.bz2
get https://ftp.gnu.org/gnu/gmp/gmp-5.0.1.tar.bz2
get https://ftp.gnu.org/gnu/mpc/mpc-1.1.0.tar.gz
get https://ftp.gnu.org/gnu/mpfr/mpfr-3.0.1.tar.bz2
sha256sum -c "$HERE/SHA256SUMS"
cp "$HERE/Dockerfile" ../..
echo "ready: docker build -t roo26-gcc $(cd ../.. && pwd)"
