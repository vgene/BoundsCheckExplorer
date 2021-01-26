#!/bin/bash

# Run the experiment on a specific core (processor #1, not #0); this further 
# reduce variance of the results
#
# Usage: ./runExp.sh exp.exe [$ARGS]

if [[ $# -eq 2 ]] ; then
    echo time taskset 0x00000002 $1 $2
    time taskset 0x00000002 $1 $2  #| grep "ns/iter"
else
    echo time taskset 0x00000002 $1 
    time taskset 0x00000002 $1 #| grep "ns/iter"
fi
