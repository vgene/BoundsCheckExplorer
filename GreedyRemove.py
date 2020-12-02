# We have original bc
# Need to generate a list of  remove-bc-exp.sh
import subprocess
import re
import os


def runOneTest(bc_fname):
    out = subprocess.check_output(['./exp.sh', 'bc_fname'])

    out = out.decode("utf-8")  # convert to string from bytes

    try:
        m = re.search(r'([\d,]) ns/iter', out)
        s = m.group(0)
        s.replace(',', '')
        result = int(s)
    except Exception:
        print("Run experiment failed")
        return None

    return result


def genFunctionRemoveFile(fn_list):
    fn_list_lines = map(lambda x: x + '\n', fn_list)
    with open("fn_rm.txt", 'w') as fd:
        fd.writelines(fn_list_lines)


def transform(ori_bc_fname, bc_fname):
    try:
        subprocess.check_call(['./transform.sh', ori_bc_fname, bc_fname])
    except subprocess.CalledProcessError:
        print("Transform remove-bc failed")
        return False

    return True


# try remove one function from remove list, if works
def greedyExperiment(fn_list, ori_bc_fname, threshold=0.05):
    rm_bc_fname = "bcrm.bc"

    def testList(fn_list):
        genFunctionRemoveFile(fn_list)
        if not transform(ori_bc_fname, rm_bc_fname):
            return None

        time_exp = runOneTest(rm_bc_fname)
        return time_exp

    # try ground truth
    time_og = testList([])
    print("original time = ", time_og, " ns/iter")

    time_all_remove = testList(fn_list)
    if time_all_remove is not None:
        print("all removed time = ", time_all_remove, " ns/iter")
    else:
        print("Abort")
        return None

    # 0.95 * time_og < time_all_remove < 1.05 * time_og
    if time_all_remove < time_og * (1 - threshold):
        # good speedup
        print("all removed shows good speedup (", time_all_remove / time_og, "), bigger than threshold (", threshold, ")")

    elif time_all_remove > time_og * (1 + threshold):
        print("all removed shows worse performance, (", time_all_remove / time_og, "),  please check")
        return
    else:
        print("all removed shows insignificant performance difference, speedup = (", time_all_remove / time_og, "),  stop here")
        return

    final_list = []
    for fn in fn_list:
        test_fn_list = fn_list
        test_fn_list.remove(fn)

        time_exp = testList(test_fn_list)

        # 0.95 * time_og < time_all_remove < 1.05 * time_og
        if time_exp < time_og * (1 - threshold):
            # good speedup
            final_list.append(fn)

    return final_list


def getFuncList(filename):

    # if file eixst
    if not os.path.isfile(filename):
        return None
        lines = []

    with open(filename, 'r') as fd:
        lines = fd.readlines()

    if lines:
        fn_list = lines
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

    final_fn_list = exp(fn_list, ORI_BC_FNAME, threshold=0.05)

    print(final_fn_list)


if __name__ == '__main__':
    main()
