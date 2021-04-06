#!/bin/bash

script_path=`realpath $0`
root_path=`dirname $script_path`

# Statically link all the rlib and outerloop prof RT
# The inline threshold is the same as Rustc

rlib_path=`rustc --print target-libdir`

clang -O3 original_$1.bc $rlib_path/*.rlib $rlib_path/*.rlib $root_path/outer-loop-prof-runtime/libOuterLoopProfRT.a -lstdc++ -ldl -lpthread -lc -lm -o exp_$1.exe -mllvm -inline-threshold=275
