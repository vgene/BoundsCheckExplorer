#!/bin/bash

script_path=`realpath $0`
root_path=`dirname $script_path`

#rm -rf ./target
#rm -rf ./explore

# the bench name has to be bench
$root_path/onebc.sh $1

cd explore
# now we have original.bc and fn.txt

if [[ $# -eq 2 ]] ; then
    $root_path/exp.sh original.bc $2
else
    $root_path/exp.sh original.bc
fi

# Test bcrm 
cp fn.txt fn_rm.txt
$root_path/transform.sh original.bc bcrm.bc 2> bcs.txt
if [[ $# -eq 2 ]] ; then
    $root_path/exp.sh bcrm.bc $2
else
    $root_path/exp.sh bcrm.bc
fi
