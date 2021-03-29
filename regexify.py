#!/usr/bin/env python3
import re
import fileinput
import os
import subprocess
import argparse

def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", "-r",
            metavar="path",
            type=str,
            help="root path from where to start source code conversions")
    parser.add_argument("--logfile", "-l",
            metavar="filename",
            type=str,
            nargs="?",
            const="changes.txt",
            help="name of the file in which to store line/column/filename of changes; "\
                    "default is 'changes.txt' in the specified root dir")
    args = parser.parse_args()
    return args.root, args.logfile

root, logfile = arg_parse()
if logfile: 
    logfile = os.path.join(root, logfile)
    logs = open(logfile, 'w')
else: 
    logs = None

mutregex_in = r'([a-zA-Z_][a-zA-Z0-9_\.]*)\.get_unchecked_mut[(]([a-zA-Z_][a-zA-Z0-9_\.]*)[)]'
mutregex_out = r'(&mut \1[\2])'
regex_in = r'([a-zA-Z_][a-zA-Z0-9_\.]*)\.get_unchecked[(]([a-zA-Z_][a-zA-Z0-9_\.]*)[)]'
regex_out = r'(&\1[\2])'
left_brack = r'\['

os.chdir(os.path.join(root))
rs_files = subprocess.run(["find", ".", "-name", "*.rs", "-type", "f"], 
        capture_output=True, text=True)
filelist = rs_files.stdout.split()

for fname in filelist:
    new_lines = []
    with open(fname, 'r') as fd:
        old_lines = fd.readlines()
        for idx, line in enumerate(old_lines): 
            # convert all instances of get_unchecked_mut (per line) one at a time
            while (match := re.search(mutregex_in, line)): 
                line = re.sub(mutregex_in, mutregex_out, line, count=1)
                start = match.span()[0]
                end = match.span()[1]
                # create temp string whose start is "start"
                # find location of '[' in tmp string
                # then add value of "start" to this location to get col
                tmp = line[start:]
                brack = re.search(left_brack, tmp)
                if not brack: 
                    exit("SHOULD HAVE FOUND A BRACKET [mut]")
                bloc = brack.span()[0]
                col = bloc + start + 1
                if col > end: 
                    exit("Column calculation is off!! [mut]")
                if logs: 
                    logs.write(str(idx + 1) + " " + 
                            str(col) + " " + 
                            fname + "\n")
            # convert all instances of get_unchecked (per line) one at a time
            while (match := re.search(regex_in, line)): 
                line = re.sub(regex_in, regex_out, line, count=1)
                start = match.span()[0]
                end = match.span()[1]
                # create temp string whose start is "start"
                # find location of '[' in tmp string
                # then add value of "start" to this location to get col
                tmp = line[start:]
                brack = re.search(left_brack, tmp)
                if not brack: 
                    exit("SHOULD HAVE FOUND A BRACKET [immut]")
                bloc = brack.span()[0]
                col = bloc + start + 1
                if col > end: 
                    exit("Column calculation is off!! [immut]")
                if logs: 
                    logs.write(str(idx + 1) + " " + 
                            str(col) + " " + 
                            fname + "\n")
            new_lines.append(line)
    with open(fname, 'w') as fd:
        fd.writelines(new_lines)
