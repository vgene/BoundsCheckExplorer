#!/bin/bash

# Generate and run experiments
#
# Usage: ./exp.sh exp.bc 

script_path=`realpath $0`
root_path=`dirname $script_path`

# $1 == benchmark name
# $2 == directory with .bc ('explore' or 'explore_regex')

cd $2
echo `pwd`
echo "--generating experiment"
$root_path/gen_regex_exp.sh $1
$root_path/run_regex_exp.sh ./exp_$1.exe
cd ..
