# We have original bc
# Need to generate a list of  remove-bc-exp.sh
import subprocess
import re
import os

ROOT_PATH = "/u/ziyangx/bounds-check/BoundsCheckExplorer"

def runOneTest(bc_fname, arg):
    out = subprocess.Popen([ROOT_PATH + '/exp.sh', bc_fname, arg], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    out, _ = out.communicate()
    out = out.decode("utf-8")  # convert to string from bytes

    try:
        m = re.search(r'Time ([0-9,.]+)', out)
        # m = re.search(r'([0-9,]+) ns/iter', out)
        s = m.group(1)
        result  = float(s.strip())
        #s = s.replace(',', '')
        #result = int(s)
    except Exception:
        print(out)
        print("Run experiment failed")
        return None

    return result


def runExpWithName(exp_name, arg):
    out = subprocess.Popen([ROOT_PATH + '/runExp.sh',  exp_name, arg], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = out.communicate()
    out = out.decode("utf-8")  # convert to string from bytes

    try:
        m = re.search(r'Time ([0-9,.]+)', out)
        # m = re.search(r'([0-9,]+) ns/iter', out)
        s = m.group(1)
        result  = float(s.strip())
        #s = s.replace(',', '')
        #result = int(s)
    except Exception:
        print(out)
        print("Run experiment failed")
        return None

    return result


def genExp(bc_fname):
    return subprocess.Popen([ROOT_PATH + '/genExp.sh', bc_fname], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def genFunctionRemoveFile(fn_list):
    fn_list_lines = list(map(lambda x: x + '\n', fn_list))
    with open("fn_rm.txt", 'w') as fd:
        fd.writelines(fn_list_lines)


def transform(ori_bc_fname, bc_fname):
    try:
        subprocess.check_call([ROOT_PATH + '/transform.sh', ori_bc_fname, bc_fname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Transform remove-bc failed")
        return False

    return True


# non blocking transform
def transformNB(ori_bc_fname, bc_fname, log=subprocess.DEVNULL):
    return subprocess.Popen([ROOT_PATH + '/transform.sh', ori_bc_fname, bc_fname], stdout=subprocess.DEVNULL, stderr=log)

# non-block transform
def transformAll(list_of_fn_lists, ori_bc_fname):
    if not os.path.exists('exps'):
        os.makedirs('exps')

    os.chdir('exps')

    child_processes = []
    fds = []
    for idx, l in enumerate(list_of_fn_lists):
        new_dir = 'exp-' + str(idx)
        os.makedirs(new_dir)
        os.chdir(new_dir)
        genFunctionRemoveFile(l)
        fd = open("bcs.txt", "w")
        p = transformNB('../../' + ori_bc_fname, 'bcrm.bc', fd)
        # start this one, and immediately return to start another
        child_processes.append(p)
        os.chdir('..')

    for p in child_processes:
        p.wait()

    for fd in fds:
        fd.close()

    child_processes = []
    for idx in range(len(list_of_fn_lists)):
        new_dir = 'exp-' + str(idx)
        os.chdir(new_dir)
        p = genExp('bcrm.bc')
        # start this one, and immediately return to start another
        child_processes.append(p)
        os.chdir('..')

    for p in child_processes:
        p.wait()

    os.chdir('..')

# try remove one function from remove list, if works
def greedyExperiment(fn_list, ori_bc_fname, arg, threshold=0.05):
    rm_bc_fname = "bcrm.bc"

    def testList(fn_list):
        genFunctionRemoveFile(fn_list)
        if not transform(ori_bc_fname, rm_bc_fname):
            return None

        time_exp = runOneTest(rm_bc_fname, arg)
        if time_exp is None:
            return None
        return time_exp

    # try ground truth
    time_og = testList([])
    if time_og is None:
        print("Abort")
        return None
    print("original time = ", time_og, "s")  # " ns/iter")

    time_all_remove = testList(fn_list)
    if time_all_remove is None:
        print("Abort")
        return None

    print("all removed time = ", time_all_remove, " ns/iter")

    # 0.95 * time_og < time_all_remove < 1.05 * time_og
    if time_all_remove < time_og * (1 - threshold):
        # good speedup
        print("all removed shows good speedup (", time_og / time_all_remove, "), bigger than threshold (", 1 + threshold, ")")

    elif time_all_remove > time_og * (1 + threshold):
        print("all removed shows worse performance, (", time_og / time_all_remove , "),  please check")
        return
    else:
        print("all removed shows insignificant performance difference, speedup = (", time_og / time_all_remove, "),  stop here")
        return

    print("testing on ", len(fn_list), " functions")

    list_of_fn_lists = []
    for fn in fn_list:
        test_fn_list = fn_list.copy()
        test_fn_list.remove(fn)
        list_of_fn_lists.append(test_fn_list)

    # generate all bc all at once
    transformAll(list_of_fn_lists, ori_bc_fname)

    final_list = []
    final_fn_list = []
    perf_list = []
    for idx, fn in enumerate(fn_list):
        test_fn_list = list_of_fn_lists[idx] 

        print("testing with function " + fn + " removed")
        time_exp = runExpWithName('exps/exp-' + str(idx) + "/exp.exe", arg)
        
        if time_exp is None:
            continue

        final_fn_list.append(fn)
        perf_list.append(time_all_remove / time_exp)
        # if relative speedup is smaller than threshold 
        if time_exp * (1 - threshold) < time_all_remove:
            # good speedup
            print("  still shows good speedup (", time_og / time_exp, ")")
            print("  relative speedup (", time_all_remove / time_exp, ")")
        else:
            final_list.append(fn)
            print("  shows significant worse performance difference, speedup = (", time_og / time_exp, ")")
            print("  relative speedup (", time_all_remove / time_exp, ")")

    print("Testing with the final list: ", final_list)
    time_final = testList(final_list)
    # 0.95 * time_og < time_all_remove < 1.05 * time_og
    if time_final < time_og * (1 - threshold):
        # good speedup
        print("  still shows good speedup (", time_og / time_final, ")")
        print("  relative speedup (", time_all_remove / time_final, ")")
    else:
        print("  shows significant worse performance difference, speedup = (", time_og / time_final, ")")
        print("  this greedy experiment failed")
    return final_list, final_fn_list,  perf_list, time_og / time_final


def getFuncList(filename):

    # if file eixst
    if not os.path.isfile(filename):
        return None
        lines = []

    with open(filename, 'r') as fd:
        lines = fd.readlines()

    if lines:
        fn_list = list(map(lambda x: x.strip(), lines))
    else:
        return None

    return fn_list


def main():
    FN_FNAME = "fn.txt"
    ORI_BC_FNAME = "original.bc"

    fn_list = getFuncList(FN_FNAME)
    if not fn_list:
        print("Function list (fn.txt) is empty or does not exist")
        return

    if not os.path.isfile(ORI_BC_FNAME):
        print(ORI_BC_FNAME + " does not exist")

    exp = greedyExperiment

    final_list, final_fn_list, perf_list, final_speedup = exp(fn_list, ORI_BC_FNAME, arg="/u/ziyangx/bounds-check/unsafe-bench/rust-brotli-decompressor/testdata/ipsum.brotli", threshold=0.05)

    final_tuple = list(zip(final_fn_list, perf_list))
    final_tuple.sort(key = lambda x: x[1])  

    lines = []
    lines.append("Final Speedup: " + str(final_speedup) + "\n\n")
    lines.append("Function, Relative Speedup\n")
    for (fn, perf) in final_tuple:
        lines.append(fn + "," + str(perf) + "\n")


    with open("greedy_result.txt", "w") as fd:
        fd.writelines(lines)


if __name__ == '__main__':
    main()
