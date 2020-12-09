#!/bin/bash

# make sure it's the remove-bc toolchain
# make sure it's the release version of LLVM 9.0.1

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

#RUSTFLAGS="-C no-prepopulate-passes -C passes=name-anon-globals -Cdebuginfo=0 -Cembed-bitcode=yes" cargo rustc --release --bench $1 -- --emit=llvm-bc  -Clto=fat

RUSTFLAGS="-C opt-level=0 -C no-prepopulate-passes -C passes=name-anon-globals -Cdebuginfo=2 -Cembed-bitcode=yes -Awarnings" cargo rustc --release --bin $1 -- --emit=llvm-bc -Clto=fat
#RUSTFLAGS="-C opt-level=3 -Cdebuginfo=2 -Cembed-bitcode=yes -Awarnings" cargo rustc --release --bin $1 -- --emit=llvm-bc -Clto=fat

mkdir -p explore
cd explore
cp ../target/release/deps/*.bc original.bc
opt -load ${root_path}/avoid-bench-inline/build/install/lib/CAT.so -avoid-bench-inline --inline-threshold=0 --inlinehint-threshold=50 -always-inline -simplifycfg original.bc -o original.bc
#opt -inline --inline-threshold=0 --inlinehint-threshold=50 -always-inline -simplifycfg original.bc -o original.bc
opt -load ${root_path}/show-fn-names/build/install/lib/CAT.so -show-bc-names -disable-output original.bc > fn.txt
