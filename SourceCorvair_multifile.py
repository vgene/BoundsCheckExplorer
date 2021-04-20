# Source Level Corvair
# Only convert get_unchecked(_mut) for now
import os
import subprocess
import pickle
import time
import argparse
import shutil
from regexify import convertFile
from GreedyRemove import runExpWithName

cargo_root=""
CLANG_ARGS=""

def getUnsafeLines(directory):
    line_nums = []

    rs_files = subprocess.run(["find", directory, "-name", "*.rs.unsafe", "-type", "f"], 
            capture_output=True, text=True)
    filelist = rs_files.stdout.split()

    for fname in filelist:
        with open(fname, 'r') as fd:
            lines = fd.readlines()

        for idx, line in enumerate(lines):
            # if "get_unchecked(" in line or "get_unchecked_mut(" in line:
            if "get_unchecked" in line:
                line_nums.append((fname, idx + 1))

    return line_nums


# for multiple file, actually modify the file in place
def genSourceExp(explore_name, exp_num, line_nums):
    os.chdir(cargo_root) # go to cargo_root

    # compile to original.bc
    dir_name = os.path.join(cargo_root, explore_name, "exp-" + str(exp_num))
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    
    fname_lines = {}
    for (old_fname, line) in line_nums:
        if old_fname not in fname_lines:
            fname_lines[old_fname] = [line]
        else:
            fname_lines[old_fname].append(line)

    for old_fname in fname_lines:
        new_fname = old_fname[:-7] # remove .unsafe
        convertFile(old_fname, new_fname, fname_lines[old_fname])


    p = subprocess.Popen(["../../../oneGenFromSource_multifile.sh", "test_bc", CLANG_ARGS]) #, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p.wait()

    os.chdir(dir_name)
    # dump the unsafe lines
    with open("unsafe_lines.txt", "w") as fd:
        fd.writelines([fname + str(num) + "\n" for (fname, num) in line_nums])

    shutil.copyfile(os.path.join(cargo_root, "target/release/test_bc"), ".")


# The first round is always by hotness

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
    parser.add_argument("--calout-fname", "-g",
            default="cal.out",
            type=str,
            help="times to run the experiment")
    args = parser.parse_args()
    return args.cargo_root, args.arg, args.output, args.clang_arg, args.p2_src, args.test_times, args.calout_fname


def iterativeExplore(threshold, inital_unsafe_list, initial_sensitiviy=0.001):

    cur_unsafe = inital_unsafe_list.copy()
    cur_baseline = quickTestBrotli(cur_unsafe, test_times=10)[1]
    print("Initial baseline:", cur_baseline)
    runs_cnt = 0
    round_cnt = 0
    sensitivity = initial_sensitiviy

    while len(cur_unsafe) > 0 and sensitivity > 0 and cur_baseline * (1 + initial_sensitiviy) < threshold:
        runs_count_this_round = len(cur_unsafe)
        # remove line one by one and test
        next_unsafe = cur_unsafe.copy()

        # generating exps
        print("Generating exps")
        quickTestBrotliGenAllRoundExp(cur_unsafe)

        # run exps
        for idx, line in enumerate(cur_unsafe):
            print("Testing with", len(cur_unsafe) - 1, "get_unchecked, with", line, "removed")
            exp_time = quickTestExpWithName(idx, 10, 1)
            print(exp_time)

            # if the new time does not exceed threshold, and
            if exp_time < threshold and exp_time < cur_baseline * (1 + sensitivity):
                next_unsafe.remove(line)

        runs_cnt += runs_count_this_round
        round_cnt += 1
        removed_lines = len(cur_unsafe) - len(next_unsafe)
        cur_unsafe = next_unsafe
        # remeasure the baseline, using the best count
        cur_baseline = quickTestBrotli(cur_unsafe, test_times=10)[1]

        print("### Round", round_cnt, ": ", runs_count_this_round, "runs,", len(cur_unsafe), "get_unchecked left"  )
        print("### New baseline:", cur_baseline)
        # increase sensitivity
        if removed_lines == 0:
            sensitivity *= 2
            if cur_baseline * (1 + sensitivity) > threshold:
                break
            print("Increase sensitivity to ", sensitivity)
        else:
            sensitivity = initial_sensitiviy
            if cur_baseline * (1 + sensitivity) > threshold:
                sensitivity = threshold/cur_baseline - 1
            print("Keep initial sensitivity", sensitivity)

    return cur_unsafe, cur_baseline

def quickTest(unsafe_lines, arg="/u/ziyangx/bounds-check/BoundsCheckExplorer/brotli-exp/silesia-5.brotli", test_times=5):
    old_fname = "src/lib-unsafe.rs"
    new_fname = "src/lib.rs"
    cargo_root = "/scratch/ziyangx/BoundsCheckExplorer/brotli-expand"

    genSourceExp("explore", "quick-test", unsafe_lines)
    print("binary generated")
    exp_name = os.path.join(cargo_root, "baseline", "exp-quick-test/exp.exe")

    quick_result= runExpWithName(exp_name, arg, test_time=test_times)
    return quick_result


if __name__ == "__main__":
    cargo_root, arg, pickle_name, clang_arg, p2_src, test_times, calout_fname = argParse()

    if not pickle_name.endswith("pkl"):
        pickle_name += ".pkl"

    if clang_arg is not None:
        CLANG_ARGS = clang_arg

    # get all lines with unsafe
    os.chdir(cargo_root)
    line_nums = getUnsafeLines(cargo_root)
    print("Running Corvair on ", len(line_nums), " bounds checks")

    # all safe baseline
    genSourceExp("baseline", "safe", [])
    exp_name = os.path.join(cargo_root, "baseline", "exp-safe/exp.exe")
    safe_time = runExpWithName(exp_name, arg, test_time=test_times)
    print("Safe baseline:", safe_time)

    # all unsafe baseline
    genSourceExp("baseline", "unsafe", line_nums)
    exp_name = os.path.join(cargo_root, "baseline", "exp-unsafe/exp.exe")
    unsafe_time = runExpWithName(exp_name, arg, test_time=test_times)
    print("Unsafe baseline:", unsafe_time)

    # remove cold baseline
    hot_lines = line_nums.copy()
    from ParseCallgrind import getColdLines_multifile

    cold_lines = getColdLines_multifile(hot_lines, calout_fname, 50)
    for i in cold_lines:
        hot_lines.remove(i)

    print("Hot code has", len(hot_lines))
    genSourceExp("baseline", "hot", hot_lines)
    exp_name = os.path.join(cargo_root, "baseline", "exp-hot/exp.exe")
    unsafe_time = runExpWithName(exp_name, arg, test_time=test_times)
    print("Hot baseline:", unsafe_time)

    ### sorted by hotness
    from ParseCallgrind import sortByHot_multifile
    hot_lines = sortByHot_multifile(hot_lines, calout_fname)
    hot_lines.extend(cold_lines)
    sorted_line_nums = hot_lines

    final_tuple = secondRoundExp(cargo_root, sorted_line_nums, arg, test_times)

    print("Top 10 Combined")
    for idx in range(min(10, len(final_tuple))):
        print(idx + 1, ": ", final_tuple[idx][1])
        print(", ".join([str(e) for e in final_tuple[idx][0]]))

    # results = {"impact_tuple": impact_tuple, "final_tuple": final_tuple, "impact_tuple_one_uncheck": impact_tuple_one_uncheck,
            # "unsafe_baseline": unsafe_time, "safe_baseline": safe_time}
    results = {"final_tuple": final_tuple,
            "unsafe_baseline": unsafe_time, "safe_baseline": safe_time}
    os.chdir(cargo_root)

    with open(pickle_name, "wb") as fd:
        pickle.dump(results, fd)

