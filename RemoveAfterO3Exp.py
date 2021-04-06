import argparse
import os
import shutil
import subprocess
from GreedyRemove import runExpWithName, transform, genExpNoLLVMPass, genExp

CLANG_ARGS = ""

def argParse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cargo-root", "-r",
            metavar="path",
            required=True,
            type=str,
            help="root path of the cargo directory")
    parser.add_argument("--arg", "-a",
            type=str,
            help="argument for the exp binary")
    args = parser.parse_args()
    return args.cargo_root, args.arg

def genO3Bc(cargo_root):
    os.chdir(cargo_root)

    # compile to original.bc
    dir_name = os.path.join(cargo_root, "baseline", "exp-safe")
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    os.chdir(dir_name)
    os.makedirs("./src", exist_ok=True)
    shutil.copyfile(os.path.join(cargo_root, "src/lib-safe.rs"), os.path.join(dir_name, "src/lib.rs"))

    p = subprocess.Popen(["../../../oneRemoveAfterO3.sh", "test_bc", CLANG_ARGS])
    p.wait()


def genRemoveAfterO0(cargo_root):
    os.chdir(os.path.join(cargo_root, "baseline", "exp-safe"))
    transform("original.bc", "bcrm-o0.bc")

    p = genExp("bcrm-o0.bc")
    p.wait()

def genRemoveAfterO3(cargo_root):
    os.chdir(os.path.join(cargo_root, "baseline", "exp-safe"))
    transform("original-o3.bc", "bcrm-o3.bc")

    p = genExpNoLLVMPass("bcrm-o3.bc")
    p.wait()

if __name__ == '__main__':
    cargo_root, arg = argParse()

    # safe baseline
    genO3Bc(cargo_root)
    p = genExp("original.bc")
    p.wait()
    exp_name = os.path.join(cargo_root, "baseline", "exp-safe/exp.exe")
    # warm up
    runExpWithName(exp_name, arg, test_time=5)

    safe_time = runExpWithName(exp_name, arg, test_time=5)
    print("Safe baseline (O3 from O0):", safe_time)

    p = genExp("original-o3.bc")
    p.wait()
    exp_name = os.path.join(cargo_root, "baseline", "exp-safe/exp.exe")
    # warm up
    runExpWithName(exp_name, arg, test_time=5)

    safe_time = runExpWithName(exp_name, arg, test_time=5)
    print("Safe baseline (O3 from O3):", safe_time)

    p = genExpNoLLVMPass("original-o3.bc")
    p.wait()
    exp_name = os.path.join(cargo_root, "baseline", "exp-safe/exp.exe")
    # warm up
    runExpWithName(exp_name, arg, test_time=5)

    safe_time = runExpWithName(exp_name, arg, test_time=5)
    print("Safe baseline (O0 from O3):", safe_time)

    # remove after O0 baseline
    genRemoveAfterO0(cargo_root)
    exp_name = os.path.join(cargo_root, "baseline", "exp-safe/exp.exe")

    # warmup
    runExpWithName(exp_name, arg, test_time=5)
    unsafe_time = runExpWithName(exp_name, arg, test_time=5)
    print("Remove after O0:", unsafe_time)

    # remove after O3 baseline
    genRemoveAfterO3(cargo_root)
    exp_name = os.path.join(cargo_root, "baseline", "exp-safe/exp.exe")

    # warmup
    runExpWithName(exp_name, arg, test_time=5)
    unsafe_time = runExpWithName(exp_name, arg, test_time=5)
    print("Remove after O3:", unsafe_time)

