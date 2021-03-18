#!/bin/bash

# Take in meta.bc, run edge prof on O3 and O0, and generate meta-with-prof.bc and meta-o3-with-prof.bc
script_path=`realpath $0`
root_path=`dirname $script_path`

# Statically link all the rlib and outerloop prof RT
# The inline threshold is the same as Rustc

rlib_path=`rustc --print target-libdir`

Input=$1
MetaO0="meta-o0"
MetaO0Prof="meta-o0-with-prof"
MetaO3="meta-o3"
MetaO3Prof="meta-o3-with-prof"

genEdgeProf() {
    echo "Generating $2"
    local in=$1
    local out=$2
    # Add Edge Prof 
    opt -pgo-instr-gen -instrprof $in.bc -o $in-prof.bc
    clang -O3 $in-prof.bc $rlib_path/*.rlib $rlib_path/*.rlib -fprofile-generate -lstdc++ -ldl -lpthread -lc -lm -o $in-prof.exe -mllvm -inline-threshold=275
    LLVM_PROFILE_FILE=edge.profraw ./$in-prof.exe
    llvm-profdata merge edge.profraw -output=edgeprof.out
    opt -block-freq -pgo-instr-use -pgo-test-profile-file=./edgeprof.out $in.bc -o $out.bc 
}

cp $Input $MetaO0.bc
opt -O3 $MetaO0.bc -o $MetaO3.bc
genEdgeProf $MetaO0 $MetaO0Prof
genEdgeProf $MetaO3 $MetaO3Prof

llvm-dis $MetaO0Prof.bc
llvm-dis $MetaO3Prof.bc
