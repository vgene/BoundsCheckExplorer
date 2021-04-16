# Source Level Corvair
# Only convert get_unchecked(_mut) for now
import os
import subprocess
import pickle
import time
import argparse
import random
from regexify import convertFile
from GreedyRemove import runExpWithName

cargo_root=""
CLANG_ARGS=""

def getUnsafeLines(fname):
    line_nums = []
    with open(fname, 'r') as fd:
        lines = fd.readlines()

    for idx, line in enumerate(lines):
        # if "get_unchecked(" in line or "get_unchecked_mut(" in line:
        if "get_unchecked" in line:
            line_nums.append(idx + 1)

    return line_nums


def genSourceExpNB(cargo_root, explore_name, old_fname, new_fname, exp_num, line_nums):
    os.chdir(cargo_root) # go to cargo_root

    # compile to original.bc
    dir_name = os.path.join(cargo_root, explore_name, "exp-" + str(exp_num))
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    os.chdir(dir_name)
    # convert and save to new file
    os.makedirs("./src", exist_ok=True)
    old_fname = os.path.join(cargo_root, old_fname)
    new_fname = os.path.join(dir_name, new_fname)
    convertFile(old_fname, new_fname, line_nums)

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


# keep everything safe, try one unsafe
def genAllOneUncheckRoundExp(cargo_root, old_fname, new_fname, all_line_nums):
    explore_abs = os.path.join(cargo_root, "explore-src-one-uncheck")

    child_processes = []
    for idx, line_num in enumerate(all_line_nums):
        test_line_nums = [line_num]

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

# Get the impact of each bounds check, different method
def oneUnsafeExp(cargo_root, old_fname, new_fname, all_line_nums, arg=None, test_times=5):
    genAllOneUncheckRoundExp(cargo_root, old_fname, new_fname, all_line_nums)

    time_list = []
    for idx, line_num in enumerate(all_line_nums):
        dir_name = os.path.join(cargo_root, "explore-src-one-uncheck", "exp-" + str(idx))
        exp_name = os.path.join(dir_name, "exp.exe")
        os.chdir(dir_name)
        time_exp, _, _ = runExpWithName(exp_name, arg, test_time=test_times)
        if time_exp is None:
            exit()

        print("Exp", idx, ",line: ", line_num, ":", time_exp)
        time_list.append(time_exp)

    impact_tuple = list(zip(all_line_nums, time_list))

    # ordered it in descending order
    impact_tuple.sort(key=lambda x: x[1], reverse=True)

    return impact_tuple

# Get the impact of each bounds check
def firstRoundExp(cargo_root, old_fname, new_fname, all_line_nums, arg=None, test_times=5):
    genAllFirstRoundExp(cargo_root, old_fname, new_fname, all_line_nums)

    time_list = []
    for idx, line_num in enumerate(all_line_nums):
        dir_name = os.path.join(cargo_root, "explore-src-r1", "exp-" + str(idx))
        exp_name = os.path.join(dir_name, "exp.exe")
        os.chdir(dir_name)
        time_exp, _, _ = runExpWithName(exp_name, arg, test_time=test_times)
        if time_exp is None:
            exit()

        print("Exp", idx, ",line: ", line_num, ":", time_exp)
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
    parser.add_argument("--calout-fname", "-g",
            default="cal.out",
            type=str,
            help="times to run the experiment")
    args = parser.parse_args()
    return args.cargo_root, args.arg, args.output, args.clang_arg, args.p2_src, args.test_times, args.calout_fname


def iterativeExplore(threshold, inital_unsafe_list, test_time=3, sensitivity=0.001):

    cur_unsafe = inital_unsafe_list.copy()
    cur_baseline = quickTestBrotli(cur_unsafe, test_times=test_time)[1]
    print("Initial baseline:", cur_baseline)
    runs_cnt = 0
    round_cnt = 0

    while len(cur_unsafe) > 0 and sensitivity > 0 and cur_baseline * (1 + sensitivity) < threshold:
        runs_count_this_round = len(cur_unsafe)
        # remove line one by one and test
        next_unsafe = cur_unsafe.copy()

        # generating exps
        print("Generating", len(cur_unsafe), "exps")
        quickTestBrotliGenAllRoundExp(cur_unsafe)

        # run exps
        min_time = -1
        min_idx = -1
        for idx, line in enumerate(cur_unsafe):
            print("Testing with", len(cur_unsafe) - 1, "get_unchecked, with", line, "removed")
            exp_time = quickTestExpWithName(idx, test_times, 1)
            print(exp_time)
            if min_time == -1 or exp_time < min_time:
                min_time = exp_time
                min_idx = idx

            # if the new time does not exceed threshold and sensitivity
            if exp_time < threshold and exp_time < cur_baseline * (1 + sensitivity):
                next_unsafe.remove(line)

        runs_cnt += runs_count_this_round
        round_cnt += 1
        removed_lines = len(cur_unsafe) - len(next_unsafe)
        if removed_lines == 0:
            if min_time != -1 and min_time < threshold:
                print("Force remove one in a round")
                next_unsafe.remove(cur_unsafe[min_idx])
            else:
                sensitivity = -1 # a hack to end the exploration
                print("End of exploration")

        cur_unsafe = next_unsafe
        # remeasure the baseline, using the best count
        cur_baseline = quickTestBrotli(cur_unsafe, test_times=test_time)[1]

        print("### Round", round_cnt, ": ", runs_count_this_round, "runs,", len(cur_unsafe), "get_unchecked left"  )
        print("### New baseline:", cur_baseline)

    return cur_unsafe, cur_baseline

def quickTestBrotli(unsafe_lines, arg="/u/ziyangx/bounds-check/BoundsCheckExplorer/brotli-exp/silesia-5.brotli", test_times=5):
    old_fname = "src/lib-unsafe.rs"
    new_fname = "src/lib.rs"
    cargo_root = "/scratch/ziyangx/BoundsCheckExplorer/brotli-expand"

    p = genSourceExpNB(cargo_root, "baseline", old_fname, new_fname, "quick-test", unsafe_lines)
    p.wait()
    print("binary generated")
    exp_name = os.path.join(cargo_root, "baseline", "exp-quick-test/exp.exe")

    quick_result= runExpWithName(exp_name, arg, test_time=test_times)
    return quick_result


# keep everything unsafe, try one safe
def quickTestBrotliGenAllRoundExp(all_line_nums):
    old_fname = "src/lib-unsafe.rs"
    new_fname = "src/lib.rs"
    cargo_root = "/scratch/ziyangx/BoundsCheckExplorer/brotli-expand"
    explore_abs = os.path.join(cargo_root, "explore-src-quick-test")

    child_processes = []
    for idx, line_num in enumerate(all_line_nums):
        test_line_nums = all_line_nums.copy()
        test_line_nums.remove(line_num)

        child_processes.append(genSourceExpNB(cargo_root, explore_abs, old_fname, new_fname, idx, test_line_nums))

    for p in child_processes:
        p.wait()

# Get the impact of combined bounds check
def quickTestExpWithName(idx, test_times=5, option=0):
    cargo_root = "/scratch/ziyangx/BoundsCheckExplorer/brotli-expand"
    arg = "/u/ziyangx/bounds-check/BoundsCheckExplorer/brotli-exp/silesia-5.brotli"
    dir_name = os.path.join(cargo_root, "explore-src-quick-test", "exp-" + str(idx))
    exp_name = os.path.join(dir_name, "exp.exe")
    os.chdir(dir_name)
    time_exp = runExpWithName(exp_name, arg, test_time=test_times)
    # time_exp, shortest_run, longest_run = runExpWithName(exp_name, arg, test_time=test_times)
    # option 0, median, option 1, shortest, option 2 longest
    return time_exp[option]


if __name__ == "__main__":
    old_fname = "src/lib-unsafe.rs"
    new_fname = "src/lib.rs"
    cargo_root, arg, pickle_name, clang_arg, p2_src, test_times, calout_fname = argParse()

    if not pickle_name.endswith("pkl"):
        pickle_name += ".pkl"

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
    safe_time = runExpWithName(exp_name, arg, test_time=test_times)
    print("Safe baseline:", safe_time)

    # all unsafe baseline
    p = genSourceExpNB(cargo_root, "baseline", old_fname, new_fname, "unsafe", line_nums)
    p.wait()
    exp_name = os.path.join(cargo_root, "baseline", "exp-unsafe/exp.exe")
    unsafe_time = runExpWithName(exp_name, arg, test_time=test_times)
    print("Unsafe baseline:", unsafe_time)

    # remove cold baseline
    hot_lines = line_nums.copy()
    from ParseCallgrind import getColdLines
    rs_fname = "src/lib.rs"
    cold_lines = getColdLines(hot_lines, calout_fname, 1, single_file=rs_fname)
    if cold_lines is None:
        print("Cold parsing failed")
        exit()

    for i in cold_lines:
        hot_lines.remove(i)

    print("Hot code has", len(hot_lines))
    p = genSourceExpNB(cargo_root, "baseline", old_fname, new_fname, "hot", hot_lines)
    p.wait()
    exp_name = os.path.join(cargo_root, "baseline", "exp-hot/exp.exe")
    hot_time = runExpWithName(exp_name, arg, test_time=test_times)
    print("Hot baseline:", hot_time)

    # # do P1, other wise the impact tuple is loaded from the pickle file
    # if p2_src is None:
    #     # start the experiment
    #     impact_tuple_one_check = firstRoundExp(cargo_root, old_fname, new_fname, line_nums, arg, test_times)

    #     print("Top 10 Impact (one checked)")
    #     for idx in range(min(10, len(impact_tuple_one_check))):
    #         print("Line ", impact_tuple_one_check[idx][0], ": ", impact_tuple_one_check[idx][1])
    # else:
    #     try:
    #         impact_tuple_one_check = impact_obj['impact_tuple']
    #     except Exception as e:
    #         print("Cannot load the impact tuple")
    #         print(e)
    #         exit()

    # # start the experiment, all but one unsafe
    # impact_tuple_one_uncheck = oneUnsafeExp(cargo_root, old_fname, new_fname, line_nums, arg, test_times)

    # print("Top 10 Impact (one unchecked)")
    # for idx in range(min(10, len(impact_tuple_one_uncheck))):
    #     print("Line ", impact_tuple_one_uncheck[idx][0], ": ", impact_tuple_one_uncheck[idx][1])
    # # end of one uncheck

    # # saved
    # results = {"impact_tuple": impact_tuple_one_check, "impact_tuple_one_uncheck": impact_tuple_one_uncheck,
    #         "unsafe_baseline": unsafe_time, "safe_baseline": safe_time, "hot_baseline": hot_time}
    # os.chdir(cargo_root)

    # with open("INTER-" + pickle_name, "wb") as fd:
    #     pickle.dump(results, fd)
    # print("Partial result dumped")

    # #sorted by from sequential
    # sorted_line_nums = line_nums.copy() 
    # final_tuple_by_sequential = secondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums, arg, test_times)

    # final_tuple = final_tuple_by_sequential
    # print("Top 10 Combined (Sequential)")
    # for idx in range(min(10, len(final_tuple))):
    #     print(idx + 1, ": ", final_tuple[idx][1])
    #     print(", ".join([str(e) for e in final_tuple[idx][0]]))

    # #sorted by from random
    # sorted_line_nums = line_nums.copy() 
    # random.shuffle(sorted_line_nums)
    # final_tuple_by_random = secondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums, arg, test_times)

    # final_tuple = final_tuple_by_random
    # print("Top 10 Combined (Random)")
    # for idx in range(min(10, len(final_tuple))):
    #     print(idx + 1, ": ", final_tuple[idx][1])
    #     print(", ".join([str(e) for e in final_tuple[idx][0]]))

    # #sorted by from one checked
    # sorted_line_nums = [x[0] for x in impact_tuple_one_check]

    # final_tuple_by_one_checked = secondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums, arg, test_times)

    # final_tuple = final_tuple_by_one_checked
    # print("Top 10 Combined (one-checked)")
    # for idx in range(min(10, len(final_tuple))):
    #     print(idx + 1, ": ", final_tuple[idx][1])
    #     print(", ".join([str(e) for e in final_tuple[idx][0]]))


    # #sorted by from one unchecked
    # impact_lines = [i[0] for i in impact_tuple_one_uncheck]
    # impact_lines.reverse()
    # sorted_line_nums = impact_lines

    # final_tuple_by_one_unchecked = secondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums, arg, test_times)

    # final_tuple = final_tuple_by_one_unchecked
    # print("Top 10 Combined (one-unchecked)")
    # for idx in range(min(10, len(final_tuple))):
    #     print(idx + 1, ": ", final_tuple[idx][1])
    #     print(", ".join([str(e) for e in final_tuple[idx][0]]))

    # sorted by hotness
    from ParseCallgrind import sortByHot
    hot_lines = sortByHot(hot_lines, calout_fname, single_file=rs_fname)
    hot_lines.extend(cold_lines)
    # sorted_line_nums = hot_lines

    # final_tuple_by_hotness = secondRoundExp(cargo_root, old_fname, new_fname, sorted_line_nums, arg, test_times)

    # final_tuple = final_tuple_by_hotness
    # print("Top 10 Combined (hotness)")
    # for idx in range(min(10, len(final_tuple))):
    #     print(idx + 1, ": ", final_tuple[idx][1])
    #     print(", ".join([str(e) for e in final_tuple[idx][0]]))

    # explorer
    threshold = unsafe_time[0] * 1.005
    final_unsafe, final_baseline = iterativeExplore(threshold, hot_lines[:41])
    print("0.5%", final_unsafe, final_baseline)

    threshold = unsafe_time[0] * 1.01
    final_unsafe, final_baseline = iterativeExplore(threshold, final_unsafe)
    print("1%", final_unsafe, final_baseline)

    threshold = unsafe_time[0] * 1.02
    final_unsafe, final_baseline = iterativeExplore(threshold, final_unsafe)
    print("2%", final_unsafe, final_baseline)

    threshold = unsafe_time[0] * 1.03
    final_unsafe, final_baseline = iterativeExplore(threshold, final_unsafe)
    print("3%", final_unsafe, final_baseline)

    threshold = unsafe_time[0] * 1.04
    final_unsafe, final_baseline = iterativeExplore(threshold, final_unsafe)
    print("4%", final_unsafe, final_baseline)

    threshold = unsafe_time[0] * 1.05
    final_unsafe, final_baseline = iterativeExplore(threshold, final_unsafe)
    print("5%", final_unsafe, final_baseline)

    threshold = unsafe_time[0] * 1.06
    final_unsafe, final_baseline = iterativeExplore(threshold, final_unsafe)
    print("6%", final_unsafe, final_baseline)

    threshold = unsafe_time[0] * 1.07
    final_unsafe, final_baseline = iterativeExplore(threshold, final_unsafe)
    print("7%", final_unsafe, final_baseline)

    threshold = unsafe_time[0] * 1.08
    final_unsafe, final_baseline = iterativeExplore(threshold, final_unsafe)
    print("8%", final_unsafe, final_baseline)
    
    # results = {"impact_tuple": impact_tuple_one_check, "impact_tuple_one_uncheck": impact_tuple_one_uncheck,
    #         "final_tuple": final_tuple_by_one_checked, "final_tuple_one_unchecked": final_tuple_by_one_unchecked,
    #         "final_tuple_hotness": final_tuple_by_hotness, "final_tuple_sequential": final_tuple_by_sequential,
    #         "final_tuple_random": final_tuple_by_random,
    #         "unsafe_baseline": unsafe_time, "safe_baseline": safe_time, "hot_baseline": hot_time}
    # os.chdir(cargo_root)

    # with open(pickle_name, "wb") as fd:
    #     pickle.dump(results, fd)

