#!/bin/bash

script_path=`realpath $0`
root_path=`dirname $script_path`

opt -load ${root_path}/remove-bc-pass/build/install/lib/CAT.so -simplifycfg -remove-bc -dce -simplifycfg -remove-bc -dce -simplifycfg $1 -o $2
