#!/bin/bash

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

# clang -O3 $1 /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib -ldl -lpthread -lc -lm -o exp.exe

clang -O3 $1 /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib /u/ziyangx/bounds-check/BoundsCheckExplorer/outer-loop-prof-runtime/libOuterLoopProfRT.a -lstdc++ -ldl -lpthread -lc -lm -o exp.exe


if [[ $# -eq 2 ]] ; then
    echo time taskset 0x20000000 ./exp.exe $2
    time taskset 0x20000000 ./exp.exe $2 #| grep "ns/iter"
else
    echo time taskset 0x20000000 ./exp.exe
    time taskset 0x20000000 ./exp.exe #| grep "ns/iter"
fi
