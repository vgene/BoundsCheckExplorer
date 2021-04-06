#!/bin/bash

# Compile a Rust crate and all its dependencies into one single bitcode

# make sure it's using the remove-bc toolchain (rustc and llvm)
# make sure it's the passes are compiled with LLVM 9.0.1

# $1 == benchmark name
# $2 == directory to put .bc in (either 'explore' or 'explore_regex')

script_path=`realpath $0`
root_path=`dirname $script_path`

RUSTFLAGS="-C opt-level=0 -C no-prepopulate-passes -C passes=name-anon-globals -Cdebuginfo=2 -Cembed-bitcode=yes -Awarnings" cargo rustc --release --bench $1 -- --emit=llvm-bc -Clto=fat

echo "--original_$1.bc"
cp target/release/deps/*.bc $2/original_$1.bc

echo "--avoid inlining"
opt -load ${root_path}/avoid-bench-inline/build/install/lib/CAT.so -avoid-bench-inline --inline-threshold=0 --inlinehint-threshold=50 -always-inline -simplifycfg $2/original_$1.bc -o $2/original_$1.bc

echo "--get fn names"
opt -load ${root_path}/show-fn-names/build/install/lib/CAT.so -show-bc-names -disable-output $2/original_$1.bc > $2/fn_$1.txt
