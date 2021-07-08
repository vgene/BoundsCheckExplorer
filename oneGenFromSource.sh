#!/bin/bash

# Compile a Rust crate and all its dependencies into one single bitcode

# make sure it's using the remove-bc toolchain (rustc and llvm)
# make sure it's the passes are compiled with LLVM 9.0.1

script_path=`realpath $0`
root_path=`dirname $script_path`

# already in explore-source/exp-xx/
ln -sf ../../Cargo.toml .
ln -sf ../../bin .

rm -rf target
RUSTFLAGS="-Awarnings $2 -C codegen-units=1" cargo build --jobs 1 --release --bin $1 > log 2>&1
#RUSTFLAGS="-C opt-level=0 -C no-prepopulate-passes -C passes=name-anon-globals -Cdebuginfo=2 -Cembed-bitcode=yes -Awarnings" cargo rustc --release --bin $1  -- --emit=llvm-bc -Clto=fat > log 2>&1
#RUSTFLAGS="-C no-prepopulate-passes -C passes=name-anon-globals -Cdebuginfo=0 -Cembed-bitcode=yes" cargo rustc --release --bench $1 -- --emit=llvm-bc  -Clto=fat
#RUSTFLAGS="-C opt-level=3 -Cdebuginfo=2 -Cembed-bitcode=yes -Awarnings" cargo rustc --release --bin $1 -- --emit=llvm-bc -Clto=fat

#cp target/release/deps/*.bc original.bc
#pwd
cp target/release/$1 exp.exe
rm -rf target
# opt -load ${root_path}/avoid-bench-inline/build/install/lib/CAT.so -avoid-bench-inline --inline-threshold=0 --inlinehint-threshold=50 -always-inline -simplifycfg original.bc -o original.bc >> log 2>&1
# #opt -inline --inline-threshold=0 --inlinehint-threshold=50 -always-inline -simplifycfg original.bc -o original.bc
# opt -load ${root_path}/show-fn-names/build/install/lib/CAT.so -show-bc-names -disable-output original.bc > fn.txt
# 
# $root_path/genExp.sh original.bc $2
