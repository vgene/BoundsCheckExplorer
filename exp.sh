#!/bin/bash

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

clang -O3 $1 /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib -ldl -lpthread -lc -lm -o exp.exe

./exp.exe | grep "ns/iter"
