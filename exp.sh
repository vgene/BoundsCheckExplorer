#!/bin/bash

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

# clang -O3 $1 /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib -ldl -lpthread -lc -lm -o exp.exe

$root_path/genExp.sh $1

if [[ $# -eq 2 ]] ; then
    # warm up
    $root_path/runExp.sh ./exp.exe $2 >/dev/null 2>&1 
    $root_path/runExp.sh ./exp.exe $2 
else
    # warm up
    $root_path/runExp.sh ./exp.exe >/dev/null 2>&1 
    $root_path/runExp.sh ./exp.exe
fi
