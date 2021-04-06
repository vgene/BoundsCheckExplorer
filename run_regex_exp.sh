#!/bin/bash

# Run the experiment on a specific core (processor #1, not #0); this further 
# reduce variance of the results
#
# Usage: ./run_regex_exp.sh exp.exe [$ARGS]

echo taskset 0x00000002 $1 --bench
taskset 0x00000002 $1 --bench
