# We have original bc
# Need to generate a list of  remove-bc-exp.sh
import argparse
import subprocess
import re
import os
import pickle

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))

def runOneTest(bc_fname, arg=None):
    if arg is not None:
        out = subprocess.Popen([ROOT_PATH + '/exp.sh', bc_fname, arg], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        out = subprocess.Popen([ROOT_PATH + '/exp.sh', bc_fname], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
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


def runExpWithName(exp_name, arg=None, test_time=10):

    time_list = []
    for i in range(test_time):
        if arg is not None:
            out = subprocess.Popen([ROOT_PATH + '/runExp.sh',  exp_name, arg], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        else:
            out = subprocess.Popen([ROOT_PATH + '/runExp.sh',  exp_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        out, _ = out.communicate()
        out = out.decode("utf-8")  # convert to string from bytes

        try:
            m = re.search(r'Time ([0-9,.]+)', out)
            # m = re.search(r'([0-9,]+) ns/iter', out)
            s = m.group(1)
            result  = float(s.strip())
            time_list.append(result)
            #s = s.replace(',', '')
            #result = int(s)
        except Exception:
            print(out)
            print("Run experiment failed")
            return None

    time_list.sort()
    # remove the first
    time_list = time_list[2:]

    # remove the last
    time_list = time_list[:-2]

    return sum(time_list) / len(time_list)


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
def transformAll(list_of_fn_lists, ori_bc_fname, dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    os.chdir(dir_name)

    child_processes = []
    fds = []
    for idx, l in enumerate(list_of_fn_lists):
        new_dir = 'exp-' + str(idx)
        if not os.path.exists(new_dir):
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


def findAllPoly(fn, fn_list):
    poly_list = []
    for fn_t in fn_list:
        l = len(fn_t)
        if fn[:len(fn) - 20] == fn_t[:len(fn_t) - 20]:
            poly_list.append(fn_t)
    return poly_list 


# try remove one function from remove list, if works
def greedyExperiment(fn_list, ori_bc_fname, arg=None, threshold=0.05):
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

    print("all removed time = ", time_all_remove, "s") #" ns/iter")

    # 0.95 * time_og < time_all_remove < 1.05 * time_og
    if time_all_remove < time_og * (1 - threshold):
        # good speedup
        print("all removed shows good speedup (", time_og / time_all_remove, "), bigger than threshold (", 1 + threshold, ")")

    elif time_all_remove > time_og * (1 + threshold):
        print("all removed shows worse performance, (", time_og / time_all_remove , "),  please check")
    else:
        print("all removed shows insignificant performance difference, speedup = (", time_og / time_all_remove, "),  stop here")

    print("testing on ", len(fn_list), "functions")

    list_of_poly_fns = []
    list_of_fn_lists = []
    addressed_list = []
    for fn in fn_list:
        if fn in addressed_list:
            continue
        poly_list = findAllPoly(fn, fn_list)
        addressed_list.extend(poly_list)

        if len(poly_list) > 1:
            print("Found :", len(poly_list), poly_list[0])

        test_fn_list = fn_list.copy()
        for f in poly_list:
            test_fn_list.remove(f)

        list_of_fn_lists.append(test_fn_list)
        list_of_poly_fns.append(poly_list) 

    print("testing on ", len(list_of_fn_lists), "poly functions")

    # generate all bc all at once
    transformAll(list_of_fn_lists, ori_bc_fname, "exps")

    final_list = []
    final_key_fn_list = []
    perf_list = []
    time_list = []

    for idx, test_fn_list in enumerate(list_of_fn_lists):
        # test_fn_list = list_of_fn_lists[idx] 

        print("testing with poly function " + str(idx) + "(*" + str(len(fn_list) - len(test_fn_list))+ ") removed")
        time_exp = runExpWithName('exps/exp-' + str(idx) + "/exp.exe", arg)
        
        if time_exp is None:
            continue

        final_key_fn_list.append(list_of_poly_fns[idx][0])  # find a representative
        perf_list.append(time_all_remove / time_exp)
        time_list.append(time_exp)
        # if relative speedup is smaller than threshold 
        if time_exp * (1 - threshold) < time_all_remove:
            # good speedup
            print("  still shows good speedup (", time_og / time_exp, ")")
            print("  relative speedup (", time_all_remove / time_exp, ")")
        else:
            final_list.extend(list_of_poly_fns[idx])
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

    return final_list, final_key_fn_list, perf_list, time_list, time_og,  time_final


def getBCs(dir_name):
    f = dir_name + "/bcs.txt"

    with open(f, 'r') as fd:
        lines = fd.readlines()

    total_bc = 0
    begin_str = "  Bounds check removed: "
    for l in lines:
        if l.startswith(begin_str):
            bc_num = int(l[len(begin_str):].strip())
            total_bc += bc_num

    return total_bc



def tryTopN(final_tuple, fn_list, ori_bc_fname, arg, N=10):
    list_of_fn_lists = [[],]
    # for i in range(N):
    #     fn_list = list(map(lambda x: x[0], final_tuple[:i+1]))
    #     list_of_fn_lists.append(fn_list)

    addressed_list = []
    for i in range(N):
        fn = final_tuple[i][0]
        poly_list = findAllPoly(fn, fn_list)
        addressed_list.extend(poly_list)
        tmp = addressed_list.copy()
        list_of_fn_lists.append(tmp)

    transformAll(list_of_fn_lists, ori_bc_fname, "tops_exps")

    idx_list = []
    time_list = []
    bc_list = []

    for idx in range(N):
        test_fn_list = list_of_fn_lists[idx] 

        print("testing with " + str(idx) + " functions removed")
        dir_name = 'tops_exps/exp-' + str(idx)
        time_exp = runExpWithName(dir_name + "/exp.exe", arg)
        bcs = getBCs(dir_name)
        
        if time_exp is None:
            continue

        print(" time: " + str(time_exp) + "s")
        idx_list.append(idx)
        time_list.append(time_exp)
        bc_list.append(bcs)

    return list(zip(test_fn_list, idx_list, time_list, bc_list))


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



def parseGreedyResults(file_name):
    with open(file_name, 'r') as fd:
        lines = fd.readlines()

    speedup_tuple = []
    for line in lines:
        fn, rel_speed = line.split(',')
        speedup_tuple.append((fn, float(rel_speed)))
    
    return speedup_tuple


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--args", nargs='?', default=None,
            help="Argument, default: None")
    args = parser.parse_args()

    return args.args


def main():
    arg = parseArgs()

    FN_FNAME = "fn.txt"
    ORI_BC_FNAME = "original.bc"

    fn_list = getFuncList(FN_FNAME)
    if not fn_list:
        print("Function list (fn.txt) is empty or does not exist")
        return

    if not os.path.isfile(ORI_BC_FNAME):
        print(ORI_BC_FNAME + " does not exist")

    exp = greedyExperiment

    final_list, final_key_fn_list, perf_list, time_list, time_og, time_final = exp(fn_list, ORI_BC_FNAME, arg=arg, threshold=0.03)

    final_tuple = list(zip(final_key_fn_list, perf_list))
    final_tuple.sort(key = lambda x: x[1])  

    lines = []
    lines.append("Final Speedup: " + str(time_og / time_final) + "\n\n")
    lines.append("Function, Relative Speedup\n")
    for (fn, perf) in final_tuple:
        lines.append(fn + "," + str(perf) + "\n")


    with open("greedy_result.txt", "w") as fd:
        fd.writelines(lines)

    # topN_file = "topN.txt"
    # speedup_tuple = parseGreedyResults(topN_file)

    result = tryTopN(final_tuple, fn_list, ORI_BC_FNAME, arg=arg, N=len(final_tuple))

    for (fn_list, idx, time, bc) in result:
        print(str(idx) + "," + str(time) + "," +  str(bc))


    final_result_dict = { 
            "time_original": time_og,
            "time_final": time_final,
            "phase1_result": time_list,
            "phase2_result":  result 
            }
    with open("all_results.pkl", 'wb') as fd:
        pickle.dump(final_result_dict, fd)

if __name__ == '__main__':
    main()
