# Parse the GEP and Branch counts of O0 and O3 versions
# to determine the life time of bounds check
# - How many are elided?
# - How many are hoisted out?
# - How many are removed?

import json
import csv

CATEGORIES = ["removed", "elided", "cold", "hoisted", "reduced", "duplicated"]

def dumpTable(o0map, o3map, features, dbgmap, filename="category.csv"):

    with open(filename, "w") as fd:
        writer = csv.writer(fd)

        title_row = ['key', "dbg"]
        title_row.extend(CATEGORIES)
        title_row.extend(['gep_st', 'gep_dy', 'br_st', 'br_dy',
            'gep_st_opt', 'gep_dy_opt', 'br_st_opt', 'br_dy_opt'])
        writer.writerow(title_row)

        for key in o0map:
            row = [key]

            if key in dbgmap:
                row.append(dbgmap[key])
            else:
                print("Key" + key + " not in debug map, weird!") 

            # Add features
            for f in CATEGORIES:
                if key in features[f]:
                    row.append("Y")
                else:
                    row.append("")

            row.extend(o0map[key])

            if key in o3map:
                row.extend(o3map[key])
            else:
                row.extend([0] * 4)

            writer.writerow(row)

def main():
    # load json files
    with open("cnts-o0.json" ,"r") as fd:
        o0map = json.load(fd)

    with open("cnts-o3.json" ,"r") as fd:
        o3map = json.load(fd)

    with open("debug-map.json", "r") as fd:
        dbgmap = json.load(fd)

    removed = []
    elided = []
    cold = []
    hoisted = []
    reduced = []
    duplicated = []

    for key, cntsO0 in o0map.items():
        # fn_name, uid = key.rsplit('-', 1)
        gep_st, gep_dy, br_st, br_dy = cntsO0

        if gep_st != 1:
            print("GEP static count is not 1, weird! In ", key)

        if br_st!= 1:
            print("Branch static count is not 1, weird! In ", key)

        if gep_dy != br_dy:
            print("Dynamic count in O0 are not equal, weird! In ", key)

        # If a bounds check GEP is not executed, it's cold 
        if gep_dy == 0:
            cold.append(key)

        # If a key is not in O3, then it's probably removed
        if key not in o3map:
            removed.append(key)
            continue

        gep_st3, gep_dy3, br_st3, br_dy3 = o3map[key]

        # If a branch is gone, it's elided
        if br_st3 == 0:
            elided.append(key)

        # if the branch executes fewer times than the GEP, might be hoisted out
        if br_dy3 < gep_dy3 and br_dy3 > 0:
            hoisted.append(key)

        if gep_st3 > gep_st:
            duplicated.append(key)

        # If both reduces, might be reduced
        if gep_dy3 < gep_dy and br_dy3 < br_dy:
            reduced.append(key)

    features = {
            "removed": removed,
            "elided": elided,
            "cold": cold,
            "hoisted": hoisted,
            "reduced": reduced, 
            "duplicated": duplicated
            }

    dumpTable(o0map, o3map, features, dbgmap)

if __name__ == "__main__":
    main()

