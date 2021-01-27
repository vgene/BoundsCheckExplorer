#!/bin/bash

# Run all benchmark experiments

script_path=`realpath $0`
root_path=`dirname $script_path`

benchmarks=( "assume_true"
             "crc-any-2.3.5"
             "geo-0.16.0"
             "jpeg-decoder-0.1.20"
             "outils-0.2.0"
             "hex-0.4.2"
             "itertools-0.9.0"
             "phf_generator-0.8.0")

# Create results folder
mkdir -p $root_path/results

for dir in "${benchmarks[@]}"
do
    cd $root_path/benchmarks/$dir
    rm -rf target
    $root_path/upperbound_exp.sh test_bc
    cd explore
    python3 $root_path/GreedyRemove.py
    cp all_results.pkl $root_path/results/$dir.pkl
done
