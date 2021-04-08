import toml
import os
import subprocess
import argparse

# load all crates that have get_unchecked(_mut)
def loadCrates(fname):
    try:
        with open(fname, "r") as fd:
            crate_list = fd.readlines()
    except Exception as e:
        print(e)
        crate_list = []

    crate_list = [s.strip() for s in crate_list]
    return crate_list


# parse dependencies from the toml
def parseToml(fname):
    try:
        with open(fname, 'r') as fd:
            obj = toml.load(fd)

        if 'dependencies' in obj:
            return obj['dependencies'].keys()
        else:
            return []
    except Exception as e:
        print(e)
        return []


# seperate all the directories
def parseApps(fname):
    dir_name = os.path.split(fname)[0]

    dirs = dir_name.split(os.sep)
    
    return dirs[1:]

# find all Cargo.toml file
def findTargetFiles(target):
    rs_files = subprocess.run(["find", target, "-name", "Cargo.toml", "-type", "f"],
            capture_output=True, text=True)
    filelist = rs_files.stdout.split()
    return filelist

def argParse():
    parser = argparse.ArgumentParser()

    parser.add_argument("--unchecked-list", "-l",
            default="unchecked_list.txt",
            type=str,
            help="the list of crates that contains get_unchecked")

    parser.add_argument("--root", "-r",
            type=str,
            required=True,
            help="the root path of the file structure")

    args = parser.parse_args()

    return args.unchecked_list, args.root

if __name__ == "__main__":
    unchecked_list_fname, root = argParse()
    unchecked_set = set(loadCrates(unchecked_list_fname))
    print(len(unchecked_set), "unchecked crates")

    filelist = findTargetFiles(root)
    print(len(filelist), "toml file to parse")

    tainted_apps = set() 
    for fname in filelist:
        deps = parseToml(fname)
        if (set(deps) & unchecked_set):
            apps = parseApps(fname)
            tainted_apps.update(apps)

    with open("tainted_apps.txt", "w") as fd:
        fd.write("\n".join(list(tainted_apps)))
