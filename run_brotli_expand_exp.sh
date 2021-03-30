#!/bin/bash

# Run brotli experiments

script_path=`realpath $0`
root_path=`dirname $script_path`

# Create results folder
mkdir -p $root_path/results

cd brotli-expand

# ./create_silesia.sh
# python3 silesia_gen.py

rm -rf target
$root_path/upperbound_exp.sh test_bc $root_path/brotli-expand/silesia-5.brotli
cd explore
python3 $root_path/GreedyRemove.py --arg $root_path/brotli-expand/silesia-5.brotli
cp all_results.pkl $root_path/results/$dir.pkl

