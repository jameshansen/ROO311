# The C compiler for ROO311: GCC 4.7.4 for RISC OS (GCCSDK release 6) as a cross-compiler, with binutils 2.24.
#
# GCC 4.7 is the last GCC that can target the machines ROO311 runs on: an ARM2 or ARM3 (armv2, armv2a), FPA
# floating point and the RISC OS procedure call standard with a stack limit register. GCC 4.8 dropped FPA and
# GCC 9 dropped everything before ARMv4.
#
# It is built on Ubuntu 14.04, the system GCCSDK's own Dockerfile names, because a 2013 compiler does not
# build with a current host compiler. fetch.sh puts the GCCSDK checkout and the source archives beside this
# file first, so the build itself downloads nothing but Ubuntu packages.
FROM ubuntu:14.04
RUN apt-get -y update && apt-get -y install \
    libtool patch wget help2man autogen m4 gcc g++ bison flex subversion gperf sed make \
    build-essential pkg-config realpath unzip texinfo
COPY gcc4 /gccsdk/gcc4
WORKDIR /gccsdk/gcc4

# ROO311 needs C only, and not the loop optimiser libraries (PPL and CLooG), which take longest to build.
RUN sed -i 's/^GCC_LANGUAGES="c,c++"/GCC_LANGUAGES="c"/; s/^GCC_USE_PPL_CLOOG=yes/GCC_USE_PPL_CLOOG=no/' Makefile

# The first run writes gccsdk-params (install to /gccsdk/cross and /gccsdk/env) and stops; the second builds.
RUN ./build-world || true
# build-world can be run again after a failure and carries on. A parallel build of GCC 4.7 sometimes compiles
# fixincludes' generated fixincl.x while it is still being written; the second pass finds it complete.
RUN bash -c 'export MAKEFLAGS="-j$(nproc)"; ./build-world || ./build-world || ./build-world' || (tail -n 150 build-cross-output.txt; false)
# ROO311: two faults in this GCC's ARM back end, both on the -Os path (toolchain/README.md has the story).
# The prologue code that pads the register list to make stack room takes a negative frame size for a count,
# and the buffer the push instruction is written into holds 100 characters where 15 registers need more.
# Only the compiler proper is rebuilt.
RUN cd /gccsdk/gcc4/srcdir/gcc/gcc/config/arm &&     sed -i 's/if (frame \&\& n \* 4 >= frame)/if (frame > 0 \&\& n * 4 >= frame)/' arm.c &&     sed -i 's/char pattern\[100\];/char pattern[256];/' arm.c arm.md &&     grep -q 'frame > 0 && n \* 4 >= frame' arm.c &&     cd /gccsdk/gcc4/builddir/cross-gcc/gcc && make -j$(nproc) cc1 &&     cp cc1 /gccsdk/cross/libexec/gcc/arm-unknown-riscos/4.7.4/cc1
ENV PATH=/gccsdk/cross/bin:/gccsdk/env/bin:$PATH
