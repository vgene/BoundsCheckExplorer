#!/bin/bash

mkdir silesia
cd silesia
wget http://sun.aei.polsl.pl/\~sdeor/corpus/silesia.zip
unzip silesia.zip
rm silesia.zip
cd ..
tar -cvf silesia.tar silesia
rm -r silesia
