# Source Level Corvair
# Only convert get_unchecked(_mut) for now
import os
import subprocess
import pickle
import time
import shutil
import argparse
from regexify import convertFile
from GreedyRemove import runExpWithName

CLANG_ARGS=""

def getUnsafeLines(fname):
    line_nums = []
    with open(fname, 'r') as fd:
        lines = fd.readlines()

    for idx, line in enumerate(lines):
        if "get_unchecked(" in line or "get_unchecked_mut(" in line:
            line_nums.append(idx + 1)

    return line_nums


def genSourceExpNB(cargo_root, explore_name, old_fname, new_fname, exp_num, line_nums):
    os.chdir(cargo_root) # go to cargo_root

    # compile to original.bc
    dir_name = os.path.join(cargo_root, explore_name, "exp-" + str(exp_num))
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    # convert and save to new file
    convertFile(old_fname, new_fname, line_nums)

    os.chdir(dir_name)

    os.makedirs("./src", exist_ok=True)
    shutil.copyfile(os.path.join(cargo_root, new_fname), os.path.join(dir_name, "src/lib.rs"))
    # dump the unsafe lines
    with open("unsafe_lines.txt", "w") as fd:
        fd.writelines([str(num) + "\n" for num in line_nums])

    p = subprocess.Popen(["../../../oneGenFromSource.sh", "test_bc", CLANG_ARGS]) #, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.2)
    return p


# keep everything unsafe, try one safe
def genAllFirstRoundExp(cargo_root, old_fname, new_fname, all_line_nums):
    explore_abs = os.path.join(cargo_root, "explore-src-r1")

    child_processes = []
    for idx, line_num in enumerate(all_line_nums):
        test_line_nums = all_line_nums.copy()
        test_line_nums.remove(line_num)

        child_processes.append(genSourceExpNB(cargo_root, explore_abs, old_fname, new_fname, idx, test_line_nums))

    for p in child_processes:
        p.wait()


# keep everything safe, add unsafe one by one
def genAllSecondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums):
    explore_abs = os.path.join(cargo_root, "explore-src-r2")

    test_line_nums = []
    child_processes = []
    for idx, line_num in enumerate(sorted_line_nums):
        test_line_nums.append(line_num)

        child_processes.append(genSourceExpNB(cargo_root, explore_abs, old_fname, new_fname, idx, test_line_nums))

    for p in child_processes:
        p.wait()


# Get the impact of each bounds check
def firstRoundExp(cargo_root, old_fname, new_fname, all_line_nums, arg=None, test_times=5):
    genAllFirstRoundExp(cargo_root, old_fname, new_fname, all_line_nums)

    time_list = []
    for idx, line_num in enumerate(all_line_nums):
        dir_name = os.path.join(cargo_root, "explore-src-r2", "exp-" + str(idx))
        exp_name = os.path.join(dir_name, "exp.exe")
        os.chdir(dir_name)
        time_exp, _, _ = runExpWithName(exp_name, arg, test_time=test_times)
        if time_exp is None:
            exit()

        print("Exp", idx, ":", time_exp)
        time_list.append(time_exp)

    impact_tuple = list(zip(all_line_nums, time_list))

    # ordered it in descending order
    impact_tuple.sort(key=lambda x: x[1], reverse=True)

    return impact_tuple


# Get the impact of combined bounds check
def secondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums, arg=None, test_times=5):
    genAllSecondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums)

    cur_lines = []
    lines_list = []
    time_list = []
    top_error_list = [] # longer
    bottom_error_list = [] # shorter

    for idx, line_num in enumerate(sorted_line_nums):
        dir_name = os.path.join(cargo_root, "explore-src-r2", "exp-" + str(idx))
        exp_name = os.path.join(dir_name, "exp.exe")
        os.chdir(dir_name)
        time_exp, shortest_run, longest_run = runExpWithName(exp_name, arg, test_time=test_times)
        if time_exp is None:
            exit()

        print("Exp", idx, ":", time_exp)
        cur_lines.append(line_num)
        time_list.append(time_exp)
        top_error_list.append(longest_run - time_exp)
        bottom_error_list.append(time_exp - shortest_run)
        lines_list.append(cur_lines.copy())

    final_tuple = list(zip(lines_list, time_list, top_error_list, bottom_error_list))

    return final_tuple


def argParse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cargo-root", "-r",
            metavar="path",
            type=str,
            help="root path of the cargo directory")
    parser.add_argument("--arg", "-a",
            type=str,
            help="argument for the exp binary")
    parser.add_argument("--output", "-o",
            type=str,
            default="final_results",
            help="output pickle name")
    parser.add_argument("--clang-arg", "-c",
            type=str,
            help="additional clang args")
    parser.add_argument("--p2-src", "-s",
            type=str,
            help="the pkl file with impact tuple, and only execute phase 2")
    parser.add_argument("--test-times", "-t",
            metavar="path",
            type=int,
            default=5,
            help="times to run the experiment")
    args = parser.parse_args()
    return args.cargo_root, args.arg, args.output, args.clang_arg, args.p2_src, args.test_times

if __name__ == "__main__":
    old_fname = "src/lib-unsafe.rs"
    new_fname = "src/lib.rs"
    cargo_root, arg, pickle_name, clang_arg, p2_src, test_times = argParse()

    if clang_arg is not None:
        CLANG_ARGS = clang_arg

    impact_obj = {}
    if p2_src is not None:
        with open(p2_src, 'rb') as fd:
            impact_obj = pickle.load(fd)

    # get all lines with unsafe
    os.chdir(cargo_root)
    line_nums = getUnsafeLines(old_fname)
    print("Running Corvair on ", len(line_nums), " bounds checks")

    # all safe baseline
    p = genSourceExpNB(cargo_root, "baseline", old_fname, new_fname, "safe", [])
    p.wait()
    exp_name = os.path.join(cargo_root, "baseline", "exp-safe/exp.exe")
    # warm up
    # runExpWithName(exp_name, arg, test_time=10)

    safe_time = runExpWithName(exp_name, arg, test_time=test_times)
    print("Safe baseline:", safe_time)

    # all unsafe baseline
    p = genSourceExpNB(cargo_root, "baseline", old_fname, new_fname, "unsafe", line_nums)
    p.wait()
    exp_name = os.path.join(cargo_root, "baseline", "exp-unsafe/exp.exe")
    # warmup
    # runExpWithName(exp_name, arg, test_time=10)
    unsafe_time = runExpWithName(exp_name, arg, test_time=test_times)
    print("Unsafe baseline:", unsafe_time)

    # do P1, other wise the impact tuple is loaded from the pickle file
    if p2_src is None:
        # start the experiment
        impact_tuple = firstRoundExp(cargo_root, old_fname, new_fname, line_nums, arg, test_times)

        print("Top 10 Impact")
        for idx in range(min(10, len(impact_tuple))):
            print("Line ", impact_tuple[idx][0], ": ", impact_tuple[idx][1])
    else:
        try:
            impact_tuple = impact_obj['impact_tuple']
        except Exception as e:
            print("Cannot load the impact tuple")
            print(e)
            exit()

    sorted_line_nums = [x[0] for x in impact_tuple]
    final_tuple = secondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums, arg, test_times)

    print("Top 10 Combined")
    for idx in range(min(10, len(final_tuple))):
        print(idx + 1, ": ", final_tuple[idx][1])
        print(", ".join([str(e) for e in final_tuple[idx][0]]))

    results = {"impact_tuple": impact_tuple, "final_tuple": final_tuple,
            "unsafe_baseline": unsafe_time, "safe_baseline": safe_time}
    os.chdir(cargo_root)

    if not pickle_name.endswith("pkl"):
        pickle_name += ".pkl"

    with open(pickle_name, "wb") as fd:
        pickle.dump(results, fd)

