def parseCallgrind(fname="callgrind.out.401080"):
    import re
    
    with open(fname, "r") as fd:
        lines = fd.readlines()

    line_cnt = {}
    for line in lines:
        if re.match("^[0-9 \n]+$", line):
            ln_cnt_list = [int(i) for i in line.split() if i.isdigit()]
            if len(ln_cnt_list) == 2:
                ln, cnt = ln_cnt_list
                if ln in line_cnt:
                    line_cnt[ln] += cnt
                else:
                    line_cnt[ln] = cnt

    return line_cnt

def getAllUncheckedLines(fname):
    with open(fname, "r") as fd:
        src_lines = fd.readlines()
    lines = []
    for idx, line in enumerate(src_lines):
        if "get_unchecked" in line:
            lines.append(idx + 1)

    return lines


def sortByHot(lines, callgrind_fname="callgrind.out.401080"):
    line_cnt = parseCallgrind(callgrind_fname)
    line_cnt_tuple = [(line, line_cnt[line]) for line in lines]

    line_cnt_tuple.sort(key=lambda item: item[1], reverse=True)

    return [item[0] for item in line_cnt_tuple]
    

def getColdLines(lines, callgrind_fname="callgrind.out.401080", threshold=5000):
    line_cnt = parseCallgrind(callgrind_fname)

    cold_lines = []
    for ln in lines:
        if ln not in line_cnt:
            cold_lines.append(ln)
        elif line_cnt[ln] < threshold:
            cold_lines.append(ln)

    return cold_lines

if __name__=="__main__":
    callgrind_fname = "/scratch/ziyangx/BoundsCheckExplorer/brotli-expand/explore/call-graph/callgrind.out.401080"
    rs_fname = "/scratch/ziyangx/BoundsCheckExplorer/brotli-expand/src/lib.rs"

    lines = getAllUncheckedLines(rs_fname)
    cold_lines = getColdLines(lines, callgrind_fname, 1000)

    for line in cold_lines:
        lines.remove(line)

    lines = sortByHot(lines, callgrind_fname)
    line_cnt = parseCallgrind(callgrind_fname)

    for k in lines:
        print(k, line_cnt[k])

    print(len(cold_lines))
