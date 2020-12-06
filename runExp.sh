#!/bin/bash

if [[ $# -eq 2 ]] ; then
    echo time taskset 0x20000000 $1 $2
    time taskset 0x20000000 $1 $2  #| grep "ns/iter"
else
    echo time taskset 0x20000000 $1 
    time taskset 0x20000000 $1 #| grep "ns/iter"
fi
