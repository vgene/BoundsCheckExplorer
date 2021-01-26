#!/bin/bash

script_path=`realpath $0`
root_path=`dirname $script_path`

# Statically link all the rlib and outerloop prof RT
# The inline threshold is the same as Rustc
clang -O3 $1 /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib /u/ziyangx/bounds-check/BoundsCheckExplorer/outer-loop-prof-runtime/libOuterLoopProfRT.a -lstdc++ -ldl -lpthread -lc -lm -o exp.exe -mllvm -inline-threshold=275
