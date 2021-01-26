#!/bin/bash

script_path=`realpath $0`
root_path=`dirname $script_path`

# the bench name has to be bench
$root_path/onebc.sh $1

cd explore
# now we have original.bc and fn.txt

# Get original prof
if [[ $# -eq 1 ]] ; then
    $root_path/prof_transform.sh original.bc original_instr.bc
else
    $root_path/prof_transform.sh original.bc original_instr.bc $2
fi

if [[ $# -eq 3 ]] ; then
    $root_path/exp.sh original_instr.bc $3
else
    $root_path/exp.sh original_instr.bc
fi
mv outer_loop_prof.txt original_prof.txt

# Get bcrm prof
cp fn.txt fn_rm.txt
$root_path/transform.sh original_instr.bc bcrm.bc 2> bcs.txt
if [[ $# -eq 3 ]] ; then
    $root_path/exp.sh bcrm.bc $3
else
    $root_path/exp.sh bcrm.bc
fi
mv outer_loop_prof.txt bcrm_prof.txt
