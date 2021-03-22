#!/bin/bash

# Compile all passes

passes=( "outer-loop-prof-instr"
         "avoid-bench-inline"
         "remove-bc-pass"
         "show-fn-names"
         "instr-cnt-dump-pass"
         "bc-life-cycle-pass")

script_path=`realpath $0`
root_path=`dirname $script_path`

for dir in "${passes[@]}"
do
    cd $root_path/$dir
    ./run_me.sh
done

cd $root_path/outer-loop-prof-runtime
make

