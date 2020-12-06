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
        print("Run experiment failed")
        return None

    return result


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
    print("original time = ", time_og, " ns/iter")

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
    final_list = []
    for fn in fn_list:
        test_fn_list = fn_list.copy()
        test_fn_list.remove(fn)

        print("testing with function " + fn + " removed")
        time_exp = testList(test_fn_list)

        # 0.95 * time_og < time_all_remove < 1.05 * time_og
        if time_exp < time_og * (1 - threshold):
            # good speedup
            print("  still shows good speedup (", time_og / time_exp, ")")
            print("  relative speedup (", time_all_remove / time_exp, ")")
        else:
            final_list.append(fn)
            print("  shows significant worse performance difference, speedup = (", time_og / time_exp, ")")

    print("Testing with the final list: ", final_list)
    time_final = testList(final_list)
    # 0.95 * time_og < time_all_remove < 1.05 * time_og
    if time_final < time_og * (1 - threshold):
        # good speedup
        print("  still shows good speedup (", time_og / time_final, ")")
        print("  relative speedup (", time_all_remove / time_final, ")")
        return final_list
    else:
        print("  shows significant worse performance difference, speedup = (", time_og / time_final, ")")
        print("  this greedy experiment failed")
        return None



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

    final_fn_list = exp(fn_list, ORI_BC_FNAME, arg="/u/ziyangx/bounds-check/unsafe-bench/rust-brotli-decompressor/testdata/ipsum.brotli", threshold=0.05)

    print(final_fn_list)


if __name__ == '__main__':
    main()
