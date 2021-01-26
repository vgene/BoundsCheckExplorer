#!/bin/bash

# Generate and run experiments
#
# Usage: ./exp.sh exp.bc 

script_path=`realpath $0`
root_path=`dirname $script_path`

$root_path/genExp.sh $1

if [[ $# -eq 2 ]] ; then
    # warm up
    $root_path/runExp.sh ./exp.exe $2 >/dev/null 2>&1 
    $root_path/runExp.sh ./exp.exe $2 
else
    # warm up
    $root_path/runExp.sh ./exp.exe >/dev/null 2>&1 
    $root_path/runExp.sh ./exp.exe
fi
