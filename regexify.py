#!/usr/bin/env python3
# Convert get_unchecked(_mut), and from_raw_parts(_mut) to safe version
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
# old_fname is the file before conversion
# new_fname is the file after conversion 
# selective unsafe contains the lines that we want to keep the unsafe
def convertFile(old_fname, new_fname, selective_unsafe=[]):
    mutregex_in = r'([($a-zA-Z_][a-zA-Z0-9:_\.\(\)\*]*)\.get_unchecked_mut\(' #]([0-9a-zA-Z_][a-zA-Z0-9_\.\>\*\+ ]*)[)]'
    mutregex_out = r'(&mut \1[' #\2])'
    regex_in = r'([($a-zA-Z_][a-zA-Z0-9:_\.\(\)\*]*)\.get_unchecked\(' #]([0-9a-zA-Z_][a-zA-Z0-9_\.\>\*\+ ]*)[)]'
    regex_out = r'(&\1[' #\2])'
    
    # handle raw parts, emitted by the macro as get_unchecked_raw(_mut)
    raw_mutregex_in = r'([$a-zA-Z_][a-zA-Z0-9:_\.\(\)]*)\.get_unchecked_raw_mut\(' #]([0-9a-zA-Z_][a-zA-Z0-9_\.\>\*\+ ]*)[)]'
    raw_mutregex_out = r'(&mut \1[' #\2])'
    raw_regex_in = r'([$a-zA-Z_][a-zA-Z0-9:_\.\(\)]*)\.get_unchecked_raw\(' #]([0-9a-zA-Z_][a-zA-Z0-9_\.\>\*\+ ]*)[)]'
    raw_regex_out = r'(&\1[' #\2])'

    with open(old_fname, 'r') as fd:
        old_block = fd.read()

    block, bcs_mut = convertBlock(old_block, mutregex_in, mutregex_out, 1, selective_unsafe)
    if block == None or bcs_mut == None:
        print("Conversion failed in file %s" % old_fname)
        exit()

    block, bcs_immut = convertBlock(block, regex_in, regex_out, 1, selective_unsafe)
    if block == None or bcs_immut == None:
        print("Conversion failed in file %s" % old_fname)
        exit()

    block, bcs_raw_mut = convertBlock(block, raw_mutregex_in, raw_mutregex_out)
    if block == None or bcs_raw_mut == None:
        print("Conversion failed in file %s" % old_fname)
        exit()

    block, bcs_raw_immut = convertBlock(block, raw_regex_in, raw_regex_out)
    if block == None or bcs_raw_immut == None:
        print("Conversion failed in file %s" % old_fname)
        exit()

    new_block = block
    bcs = bcs_mut + bcs_immut + bcs_raw_mut + bcs_raw_immut 

    with open(new_fname, 'w') as fd:
        fd.write(new_block)

    # add fname to the bcs
    bcs = [ (line, col, new_fname) for (line, col) in bcs ] 

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
def convertBlock(block, regex_in, regex_out, cur_line=1, selective_unsafe=[]):
    bcs = []
    new_block = ""

    # convert all instances of regex_in (per line) one at a time
    while (match := re.search(regex_in, block)): 
        # put whatever before in it 
        pre_block = block[:match.span()[0]]
        cur_block = block[match.span()[0]:match.span()[1]]
        post_block = block[match.span()[1]:]

        # handle within function call
        # foo(xx.get_uncheck(

        right = 0
        for idx in reversed(range(len(cur_block) - 1)): # exclude the last '('
            if cur_block[idx] == ')':
                right += 1
            if cur_block[idx] == '(':
                right -= 1
            if right < 0:
                # found function start
                pre_block += cur_block[:idx+1]
                cur_block = cur_block[idx + 1:]
                break

        # calculate line and col
        skipped_lines = pre_block.count('\n')
        cur_line += skipped_lines

        # the column number of the starting point of old block
        old_col = pre_block.rfind('\n')
        if old_col == -1:
            old_col = len(pre_block) + 1
        else:
            old_col = len(pre_block) - old_col

        # if choose not to convert this line to safe
        if cur_line in selective_unsafe:
            new_block += pre_block + cur_block
            block = post_block
            continue

        # find match parenthesis in post_block
        pos = findMatchingParenthsis(post_block)
        # self.get_unchecked() syntax, need to ignore
        if pos == 0: 
            new_block += pre_block + cur_block
            block = post_block
            continue

        if pos == -1:
            print("No enclosing parenthesis found, Line %d" % (cur_line))
            return None, None

        # replace with the safe syntax
        cur_block = re.sub(regex_in, regex_out, cur_block, count=1)
        new_col = old_col + len(cur_block) - 1

        new_middle_block, addition_bcs = convertBlock(post_block[:pos], regex_in, regex_out, cur_line, selective_unsafe)

        # add bounds checks from the middle block to the bcs
        if addition_bcs is None:
            return None, None
        else:
            bcs.extend(addition_bcs)

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
        bcs.extend(convertFile(fname, fname))

    dumpBCs(bcs, logfile)

