#!/bin/bash

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

opt -loop-simplify -load $root_path/outer-loop-prof-instr/build/install/lib/CAT.so -outer-loop-prof-instr $1 -o $2
