#!/bin/bash

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

opt -load ${root_path}/remove-bc-pass/build/install/lib/CAT.so -simplifycfg -remove-bc -dce -simplifycfg -remove-bc -dce -simplifycfg $1 -o $2
