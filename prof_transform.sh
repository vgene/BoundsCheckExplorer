#!/bin/bash

script_path=`realpath $0`
root_path=`dirname $script_path`

exp_depth=0
if [[ $# -eq 3 ]] ; then
    exp_depth=$3
fi

opt -loop-simplify -load $root_path/outer-loop-prof-instr/build/install/lib/CAT.so -outer-loop-prof-instr -exp-depth=$exp_depth $1 -o $2
