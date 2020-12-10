
#!/bin/bash

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

benchmarks=("outils-0.2.0" "itertools-0.9.0" )

# benchmarks=( "assume_true" "crc-any-2.3.5" "fancy-regex-0.4.1" "geo-0.16.0"  "jpeg-decoder-0.1.20"  "outils-0.2.0"
#     "hex-0.4.2" "itertools-0.9.0" "phf_generator-0.8.0")
for dir in "${benchmarks[@]}"
do
    cd $root_path/benchmarks/$dir
    rm -rf target
    $root_path/upperbound_exp.sh test_bc
    cd explore
    python $root_path/GreedyRemove.py
    cp all_results.pkl $root_path/benchmarks/results/$dir.pkl
done
