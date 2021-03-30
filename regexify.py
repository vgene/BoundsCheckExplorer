#!/usr/bin/env python3
import re
import os
import subprocess
import argparse


# [(line, col, fname), ...]
def dumpBCs(bcs, logfile=None):
    if not logfile:
        return

    with open(logfile, 'w') as fd:
        for (line, col, fname) in bcs:
            # get rid of the initial "./"
            if fname.startswith("./"):
                fname = fname[2:]

            # dump with the format that remove-bc pass can recognize
            fd.write("%d %d %s\n" % (line, col, fname))


def argParse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", "-r",
            metavar="path",
            type=str,
            help="root path from where to start source code conversions")
    parser.add_argument("--single-file", "-s",
            metavar="filename",
            type=str,
            nargs="?",
            help="Specify this if only want to apply this tool to a single file")
    parser.add_argument("--logfile", "-l",
            metavar="filename",
            type=str,
            nargs="?",
            const="changes.txt",
            default="changes.txt",
            help="name of the file in which to store line/column/filename of changes; "\
                    "default is 'changes.txt' in the specified root dir")
    args = parser.parse_args()
    return args.root, args.logfile, args.single_file


def findTargetFiles(single_file):
    # files
    if single_file:
        target = single_file
    else:
        target = "."
    rs_files = subprocess.run(["find", target, "-name", "*.rs", "-type", "f"], 
            capture_output=True, text=True)
    filelist = rs_files.stdout.split()
    return filelist


# Convert all things in place in one file
def convertFile(fname):
    mutregex_in = r'([a-zA-Z_][a-zA-Z0-9:_\.\(\)]*)\.get_unchecked_mut\(' #]([0-9a-zA-Z_][a-zA-Z0-9_\.\>\*\+ ]*)[)]'
    mutregex_out = r'(&mut \1[' #\2])'
    regex_in = r'([a-zA-Z_][a-zA-Z0-9:_\.\(\)]*)\.get_unchecked\(' #]([0-9a-zA-Z_][a-zA-Z0-9_\.\>\*\+ ]*)[)]'
    regex_out = r'(&\1[' #\2])'

    with open(fname, 'r') as fd:
        old_block = fd.read()

    block, bcs_mut = convertBlock(old_block, mutregex_in, mutregex_out)
    if block == None or bcs_mut == None:
        print("Conversion failed in file %s" % fname)
        exit()

    new_block, bcs_immut = convertBlock(block, regex_in, regex_out)
    if new_block == None or bcs_immut == None:
        print("Conversion failed in file %s" % fname)
        exit()

    bcs = bcs_mut + bcs_immut

    with open(fname, 'w') as fd:
        fd.write(new_block)

    # add fname to the bcs
    bcs = [ (line, col, fname) for (line, col) in bcs ] 

    return bcs


# already have a left parenthesis, find the matching right parenthesis
def findMatchingParenthsis(block):
    depth = 1

    for pos, ch in enumerate(block):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if depth == 0:
            return pos

    # failed case 
    return -1

# when a x.get_unchecked( or x.get_unchecked_mut( is found
# Step 1: go back and replace the handle with regex
# Step 2: go forward and find matching parenthesis, replace it as "])"
# Step 3: convert whatever is inside
def convertBlock(block, regex_in, regex_out):
    bcs = []
    new_block = ""

    cur_line = 1
    # convert all instances of regex_in (per line) one at a time
    while (match := re.search(regex_in, block)): 
        # put whatever before in it 
        pre_block = block[:match.span()[0]]
        cur_block = block[match.span()[0]:match.span()[1]]
        post_block = block[match.span()[1]:]

        # calculate line and col
        skipped_lines = pre_block.count('\n')
        cur_line += skipped_lines

        # the column number of the starting point of old block
        old_col = pre_block.rfind('\n')
        if old_col == -1:
            old_col = len(pre_block) + 1
        else:
            old_col = len(pre_block) - old_col

        # replace with the safe syntax
        cur_block = re.sub(regex_in, regex_out, cur_block, count=1)
        new_col = old_col + len(cur_block) - 1

        # find match parenthesis in post_block
        pos = findMatchingParenthsis(post_block)
        if pos == -1:
            print("No enclosing parenthesis found, Line %d" % (cur_line))
            return None, None

        new_middle_block, addition_bcs = convertBlock(post_block[:pos], regex_in, regex_out)

        # adjust the line based on current line
        for (line, col) in addition_bcs:
            bcs.append((line + cur_line - 1, col))

        # update new block
        new_block += pre_block + cur_block + new_middle_block + "])"  # use the right parenthesis

        # update block
        block = post_block[pos + 1:]

        # update bcs
        bcs.append((cur_line, new_col))

        # might have skipped several lines in the middle block
        skipped_lines = new_middle_block.count('\n')
        cur_line += skipped_lines

    # append whatever is left in the block
    new_block += block

    return new_block, bcs


if __name__ == "__main__":
    root, logfile, single_file = argParse()
    os.chdir(root)

    filelist = findTargetFiles(single_file)
    
    print("Converting files: ", filelist)

    # List of all bounds checks
    bcs = []
    for fname in filelist:
        bcs.extend(convertFile(fname))

    dumpBCs(bcs, logfile)

