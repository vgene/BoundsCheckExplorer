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

def parseCalout(fname="cal.out"):
    with open(fname, 'r') as fd:
        lines = fd.readlines()

    m = {}
    for line in lines:
        cnt, _ , ln, f, _  = line.split(',')
        if cnt:
            cnt = int(cnt)
        else:
            cnt = 0
        ln = int(ln)
        if f in m:
            m[f][ln] = cnt
        else:
            m[f] = {ln: cnt}
    return m


def sortByHot(lines, calout_fname, single_file=None):
    m = parseCalout(calout_fname)

    if single_file is not None:
        if single_file not in m:
            return None

        line_cnt = m[single_file]
        for line in lines:
            if line not in line_cnt:
                line_cnt[line] = 0

        line_cnt_tuple = [(line, line_cnt[line]) for line in lines]
        line_cnt_tuple.sort(key=lambda item: item[1], reverse=True)
        return [item[0] for item in line_cnt_tuple]
    else:
        for (fname, line) in lines:
            if fname not in m:
                m[fname] = {line: 0}
            else:
                if line not in m[fname]:
                    m[fname][line] = 0

        line_cnt_tuple = [((fname, line), m[fname][line]) for (fname, line) in lines]
        line_cnt_tuple.sort(key=lambda item: item[1], reverse=True)
        return [item[0] for item in line_cnt_tuple]


def getColdLines(lines, calout_fname, threshold=5000, single_file=None):
    m = parseCalout(calout_fname)

    if single_file is not None:
        if single_file not in m:
            return None

        line_cnt = m[single_file]

        cold_lines = []
        for ln in lines:
            if ln not in line_cnt:
                cold_lines.append(ln)
            elif line_cnt[ln] < threshold:
                cold_lines.append(ln)

        return cold_lines
    else:
        cold_lines = []
        for (fname, line) in lines:
            if fname not in m:
                cold_lines.append((fname, line))
            else:
                if line not in m[fname]:
                    cold_lines.append((fname, line))
                elif m[fname][line] < threshold:
                    cold_lines.append((fname, line))

        return cold_lines

def sortByHot_old(lines, callgrind_fname="callgrind.out.401080"):
    line_cnt = parseCallgrind(callgrind_fname)
    line_cnt_tuple = [(line, line_cnt[line]) for line in lines]

    line_cnt_tuple.sort(key=lambda item: item[1], reverse=True)

    return [item[0] for item in line_cnt_tuple]
    

def getColdLines_old(lines, callgrind_fname="callgrind.out.401080", threshold=5000):
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
    calout_fname = "/scratch/ziyangx/BoundsCheckExplorer/brotli-expand/cal.out"
    rs_fname = "src/lib.rs"

    lines = getAllUncheckedLines("/scratch/ziyangx/BoundsCheckExplorer/brotli-expand/src/lib-unsafe.rs") #rs_fname)
    cold_lines = getColdLines(lines, calout_fname, 1, single_file=rs_fname)

    for line in cold_lines:
        lines.remove(line)

    lines = sortByHot(lines, calout_fname, single_file=rs_fname)
    line_cnt = parseCalout(calout_fname)[rs_fname]

    for k in lines:
        print(k, line_cnt[k])

    print(len(lines))
    print(len(cold_lines))
