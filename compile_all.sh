#!/bin/bash

# Compile all passes

passes=( "outer-loop-prof-instr"
         "outer-loop-prof-runtime"
         "avoid-bench-inline"
         "remove-bc-pass"
         "show-fn-names" )

script_path=`realpath $0`
root_path=`dirname $script_path`

for dir in "${passes[@]}"
do
    cd $root_path/$dir
    ./run_me.sh
done
