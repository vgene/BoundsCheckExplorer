#!/bin/bash

# Check whether the modified IRCE pass make a difference
# Not included in the paper

script_path=`realpath $0`
root_path=`dirname $script_path`

#opt --licm --indvars --simplifycfg --loop-simplify --lcssa --loop-rotate --irce original.bc -o new_pass.bc
#opt --irce-print-range-checks=true --irce-print-changed-loops=true --irce-loop-size-cutoff=200 --irce-skip-profitability-checks=true --irce original.bc -o new_pass.bc
#benchmarks=("hex-0.4.2")

benchmarks=( "assume_true" "crc-any-2.3.5" "geo-0.16.0"  "jpeg-decoder-0.1.20"  "outils-0.2.0"
             "hex-0.4.2" "itertools-0.9.0" "phf_generator-0.8.0")

for dir in "${benchmarks[@]}"
do
    cd $root_path/benchmarks/$dir/explore

    opt -O3 --irce original.bc -o new_pass.bc

    echo $dir
    $root_path/exp.sh new_pass.bc 2>&1 >/dev/null
    taskset 0x00000002 ./exp.exe

    $root_path/exp.sh original.bc 2>&1 >/dev/null
    taskset 0x00000002 ./exp.exe

    echo " "
    echo " "
    echo " "
done
