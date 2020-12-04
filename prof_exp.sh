#!/bin/bash

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

# the bench name has to be bench
$root_path/onebc.sh $1

cd explore
# now we have original.bc and fn.txt

# Get original prof
$root_path/prof_transform.sh original.bc original_instr.bc
$root_path/exp.sh original_instr.bc 
mv outer_loop_prof.txt original_prof.txt

# Get bcrm prof
cp fn.txt fn_rm.txt
$root_path/transform.sh original_instr.bc bcrm.bc
$root_path/exp.sh bcrm.bc 
mv outer_loop_prof.txt bcrm_prof.txt
