# Python 3
#
# Ziyang Xu
# Dec 09-10, 2020
#
# Present the OSDI cache paper results in HTML, plots,
# and a bunch of interesting stuff

import argparse
import os
import json
from dash.dependencies import ALL
import numpy as np
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import pickle 
import scipy.stats as st

from os import path

from pprint import pprint
from collections import defaultdict

# BENCHMARK_LIST = ["assume_true", "crc-any-2.3.5", "geo-0.16.0", "hex-0.4.2", "rust-brotli-decompress-2.3.1",
#                   "jpeg-decoder-0.1.20", "outils-0.2.0",  "phf_generator-0.8.0", "itertools-0.9.0"]
# BENCHMARK_LIST = ["brotli-expand"]
BENCHMARK_LIST = []
# BENCHMARK_LIST = [ "brotli_llvm11_vec_fixed_order", "brotli_llvm11_no_vec_fixed_order",
        # "brotli_llvm9_vec_fixed_order", "brotli_llvm11_vec_cargo_fixed_order", "brotli_llvm11_no_vec_cargo_fixed_order", "brotli_llvm11_vec_cargo_fixed_order_2",
        # "brotli_llvm11_vec_cargo_fixed_order_valgrind", "brotli_llvm11_vec_cargo", 'brotli_llvm11_vec_cargo_exp']
        # # "brotli_llvm9_no_vec_fixed_order", ]
        # #"brotli_llvm11_no_vec", "brotli_llvm11_vec", "brotli_llvm9_no_vec", "brotli_llvm9_vec"]
        # #["brotli_no_vec", "brotli_normal", "brotli_llvm11"]

MAX_B_VARIANCE=0
MAX_T_VARIANCE=0
ALL_VARIANCE=[]

class ResultProvider:

    def __init__(self, path):
        self._path = path
        self._results = None

    def parsePickle(self, root_path):
        results = {}
        for filename in os.listdir(root_path):
            if filename.endswith(".pkl"):
                benchmark = filename[:len(filename) - 4]
                filename =  root_path + "/" + filename

                if path.isfile(filename):
                    with open(filename, 'rb') as fd:
                        d = pickle.load(fd)
                    BENCHMARK_LIST.append(benchmark)

                    results[benchmark] = d

        self._results = results

    def getBarResult(self, benchmark):
        time_safe = self._results[benchmark]['safe_baseline'][0]
        time_unsafe = self._results[benchmark]['unsafe_baseline'][0]

        lines = []
        speedups = []
        slowdowns = []
        for idx, item in enumerate(self._results[benchmark]["impact_tuple"]):
            lines.append(item[0])
            one_uncheck_item = self._results[benchmark]["impact_tuple_one_uncheck"][idx]
            speedups.append((time_safe / one_uncheck_item[1] - 1) *100)

            slowdowns.append((item[1] / time_unsafe - 1) * 100)

        return lines, speedups, slowdowns

    def getSourceCorvairPairs(self, benchmark):
        fns = [0]
        speedups = [1.0]
        time_original = self._results[benchmark]['safe_baseline']
        if type(time_original) is tuple:
            time_original = time_original[0]

        for idx, item in enumerate(self._results[benchmark]["final_tuple"]):
            fns.append(idx + 1)
            speedups.append((time_original / item[1] - 1) *100)

        return fns, speedups

    def getAbsoluteTime(self, benchmark):
        fns = []
        time_original = self._results[benchmark]['safe_baseline']
        fns.append(0)

        if type(time_original) is tuple:
            times = [time_original[0]]
            top_error = [time_original[2] - time_original[0]]
            bottom_error = [time_original[0] - time_original[1]]
        else:
            times = [time_original]
            top_error = [0]
            bottom_error = [0]

        for idx, item in enumerate(self._results[benchmark]["final_tuple"]):
            fns.append(idx + 1)
            times.append(item[1])
            top_error.append(item[2])
            bottom_error.append(item[3])

        return fns, times, top_error, bottom_error


    def getRelativeTimeWithName(self, benchmark, name):

        if name == "One-Checked":
            mykey = "final_tuple"
        elif name == "One-Unchecked":
            mykey = "final_tuple_one_unchecked"
        elif name == "Hotness":
            mykey = "final_tuple_hotness"
        elif name == "Random":
            mykey = "final_tuple_random"
        else:
            print("Wrong name")
            exit()

        fns = []
        time_original = self._results[benchmark]['safe_baseline']
        unsafe_time = self._results[benchmark]['unsafe_baseline']
        fns.append(0)

        def overhead(time):
            return (time / unsafe_time[0] - 1) * 100

        def calcCI(time_list, time):
            time_list = time_list[:9]
            print(time_list)
            CI = st.t.interval(alpha=0.95, df=len(time_list)-1, loc=np.mean(time_list), scale=st.sem(time_list)) 
            top = CI[1] - time
            bottom = time - CI[0]
            print(CI[0], CI[1], time, top, bottom)
            return top, bottom

        times = [overhead(time_original[0])]
        top_error = [overhead(time_original[2]) - overhead(time_original[0])]
        bottom_error = [overhead(time_original[0]) - overhead(time_original[1])]


        for idx, item in enumerate(self._results[benchmark][mykey]):
            fns.append(idx + 1)
            times.append(overhead(item[1]))
            top, bottom = calcCI(item[4], item[1])
            global MAX_T_VARIANCE
            global MAX_B_VARIANCE
            global ALL_VARIANCE
            if top > MAX_T_VARIANCE:
                MAX_T_VARIANCE = top
            if bottom > MAX_B_VARIANCE:
                MAX_B_VARIANCE = bottom
            ALL_VARIANCE.append((top, bottom))
            top_error.append((top / unsafe_time[0]) * 100)
            bottom_error.append((bottom / unsafe_time[0]) * 100)
            # top_error.append((item[2] / unsafe_time[0]) * 100)
            # bottom_error.append((item[3] / unsafe_time[0]) * 100)

        return fns, times, top_error, bottom_error

    def getRelativeTime(self, benchmark):
        fns = []
        time_original = self._results[benchmark]['safe_baseline']
        unsafe_time = self._results[benchmark]['unsafe_baseline']
        fns.append(0)

        def overhead(time):
            return (time / unsafe_time[0] - 1) * 100

        times = [overhead(time_original[0])]
        top_error = [overhead(time_original[2]) - overhead(time_original[0])]
        bottom_error = [overhead(time_original[0]) - overhead(time_original[1])]

        for idx, item in enumerate(self._results[benchmark]["final_tuple"]):
            fns.append(idx + 1)
            times.append(overhead(item[1]))
            top_error.append((item[2] / unsafe_time[0]) * 100)
            bottom_error.append((item[3] / unsafe_time[0]) * 100)

        return fns, times, top_error, bottom_error

    def getPhase2Pairs(self, benchmark):
        if benchmark.startswith("brotli"):
            return self.getSourceCorvairPairs(benchmark)

        fns = []
        speedups = []

        if benchmark not in self._results:
            return None, None

        if 'phase2_result' in self._results[benchmark]:
            (_, _, time, _) = self._results[benchmark]['phase2_result'][0]
            time_original = time
        else:
            return None, None

        for (_, idx, time, _) in self._results[benchmark]['phase2_result']:
            fns.append(idx)
            speedups.append((time_original/time - 1 ) * 100)

        return fns, speedups

    def updateResult(self):
        self.parsePickle(self._path)


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--root-path", type=str, required=True,
                        help="Root path of CPF benchmark directory")
    parser.add_argument("-g", "--gen-figs", action="store_true",
                        help="Generate figures")
    args = parser.parse_args()

    return args.root_path, args.gen_figs


# some setting for plot
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config.suppress_callback_exceptions = True


def getPlotMainLayout():
    benchmark_options = []

    for benchmark in sorted(BENCHMARK_LIST):
        benchmark_options.append({'label': benchmark, 'value': benchmark})

    layout = html.Div([
        dcc.Dropdown(
            id='benchmark-dropdown',
            options=benchmark_options,
            value="assume_true",
        ),
        html.Div(id='dd-output-container')
    ])

    return layout


def getPlotBarLayout():
    benchmark_options = []

    for benchmark in sorted(BENCHMARK_LIST):
        benchmark_options.append({'label': benchmark, 'value': benchmark})

    layout = html.Div([
        dcc.Dropdown(
            id='benchmark-dropdown-2',
            options=benchmark_options,
            value="brotli_llvm11_vec_cargo_exp",
        ),
        html.Div(id='dd-output-container-2')
    ])

    return layout


@app.callback(
    dash.dependencies.Output('dd-output-container', 'children'),
    [dash.dependencies.Input('benchmark-dropdown', 'value'), ])
def getOneBenchmarkLayout(benchmark="brotli_llvm11_vec_cargo_exp"):

    fig = getOneBenchmarkFig(benchmark)

    if fig:
        layout = [html.Div(children='Plot of ' + benchmark),
                  dcc.Graph(
            id='bmark-graph',
            figure=fig)]
    else:
        layout = None

    return layout


@app.callback(
    dash.dependencies.Output('dd-output-container-2', 'children'),
    [dash.dependencies.Input('benchmark-dropdown-2', 'value'), ])
def getBarLayout(benchmark="brotli_llvm11_vec_cargo_exp"):

    fig = getBarFig(benchmark)

    if fig:
        layout = [html.Div(children='Plot of ' + benchmark),
                html.Br(),
                html.Div(children="""
                Speedup is making one bounds check unchecked, the others still checked;
                Slowdown is making one bounds check checked, the others unchecked.
                The set is only the ones that programmers have made 'get_unchecked'.
                Both speedups and slowdowns are expected to be a positive number.
                """),
                  dcc.Graph(
            id='bmark-graph',
            figure=fig)]
    else:
        layout = None

    return layout


def getBarFig(benchmark):
    lines, rel_speedups, rel_slowdowns = app._resultProvider.getBarResult(benchmark)
    
    t = list(zip(lines, rel_speedups, rel_slowdowns))
    t.sort(key=lambda x: x[0])
    lines, rel_speedups, rel_slowdowns = zip(*t)

    lines = [str(i) for i in lines]
    bar_speedups = {'x': lines, 'y': rel_speedups, 'type': 'bar', 'name': 'speedup over all safe'}
    bar_slowdowns = {'x': lines, 'y': rel_slowdowns, 'type': 'bar', 'name': 'slowdowns over all unsafe'}

    bar_list = [bar_speedups, bar_slowdowns]

    fig = go.Figure({
        'data': bar_list,
        'layout': {
            'legend': {'orientation': 'h', 'x': 0.0, 'y': 1.05}, #1.88
            'yaxis': {
                'zeroline': True,
                'zerolinewidth': 1,
                'zerolinecolor': 'rgb(200, 200, 200)',
                'showline': True,
                'linewidth': 1,
                'ticks': "inside",
                'mirror': 'all',
                'linecolor': 'black',
                'gridcolor':'rgb(200,200,200)',
                # 'range': [0, 10],
                'nticks': 15,
                'ticksuffix': "%",
                },
            'xaxis': {
                'linecolor': 'black',
                'showline': True,
                'linewidth': 1,
                'mirror': 'all'
                },
            'font': {'family': 'Helvetica', 'color': "Black"},
            'plot_bgcolor': 'white',
            'autosize': False,
            'width': 3000,
            'height': 400}
        })

    return fig


#def getComparisonFig(benchmarks, show_legend=False, show_title=False, names=None):
def getComparisonFig(onebenchmark, show_legend=False, show_title=False, names=None):
# def getComparisonFig(show_legend=False, show_title=False, names=None):
    color_list =['#a6cee3', '#ffff99', '#1f78b4', '#6a3d9a','#fb9a99',
            '#fdbf6f','#cab2d6', '#ff7f00', '#b2df8a', '#e31a1c',
            '#33a02c','#b15928']
    shape_list = ["star", "star-square", "cross", "circle",
            "square", "square-open", "circle-open", "x",
            "triangle-up", "triangle-up-open", "diamond", "diamond-open"]

    scatter_list = []
    benchmark = onebenchmark[0]
    for idx, name in enumerate(names):
        xs, ys, top_error, bottom_error = app._resultProvider.getRelativeTimeWithName(benchmark, name)
        ys.reverse()
        ys = [-item for item in ys]

        if name == "Hotness":
            color = "#fdae61"
            shape = "circle"
        elif name == "One-Checked":
            color = "#abd9e9"
            shape = "diamond"
        elif name == "One-Unchecked":
            color = "#fee090"
            shape = "x"
        elif name == "Random":
            color = "#d7191c"
            shape = "square"
        # color = '#0429A1'
        # shape = 0

        if xs is None or ys is None:
            return None
    
        scatter_list.append(go.Scatter(x=xs, y=ys,  line={'color': color, 'width':2},
            error_y=dict(type='data', symmetric=False, array=top_error, color='rgba(5,5,5, 0.3)', arrayminus=bottom_error),
                                       marker={"symbol": shape,
                                               "size": 8, 'opacity': 1},
                                       mode='lines+markers',
                                       name=name, showlegend=show_legend))

    # # manual add brotli results
    # xs = [263, 262, 261, 257, 254, 247, 222]
    # xs.reverse()
    # ys = [-7.7, -4.4, -3.0, -1.8, -0.9, -0.3, 0]
    # ys.reverse()

    # # scatter_list.append(go.Scatter(x=xs, y=ys, line={'color': '#fdae61', 'width': 4},

    # scatter_list.append(go.Scatter(x=xs, y=ys, line={'color': '#2c7bb6', 'width': 2.5},
        # marker={"symbol": "star",
            # "size": 10, 'opacity': 1},
        # mode='lines+markers',
        # name="NADER", showlegend=show_legend))

    # xs = [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    # xs.reverse()
    # ys = [-0.0, -0.1, -0.0, -0.0, 0.1, -0.0, -0.2, 0.0, -7.3, -11.8]
    # # ys.reverse()

    # scatter_list.append(go.Scatter(x=xs, y=ys, line={'color': '#fdae61', 'width': 2.5},
            # # error_y=dict(type='data', symmetric=False, array=top_error, color='rgba(5,5,5, 0.3)', arrayminus=bottom_error),
            # marker={"symbol": "circle",
            # "size": 10, 'opacity': 1},
        # mode='lines+markers',
        # name="Hotness", showlegend=show_legend))

    # xs = [7, 8, 9]
    # # xs.reverse()
    # ys = [0.0, -3.9, -11.8]
    # # ys.reverse()

    # scatter_list.append(go.Scatter(x=xs, y=ys, line={'color': '#2c7bb6', 'width': 2.5},
        # marker={"symbol": "star",
            # "size": 10, 'opacity': 1},
        # mode='lines+markers',
        # name="NADER", showlegend=show_legend))
    height = 350

    fig = go.Figure({
        'data': scatter_list,
        'layout': {
                    'legend': {'orientation': 'h', 'x': 0.05, 'y': 1.1},
                    'yaxis': {
                        'zeroline': True,
                        'zerolinewidth': 1,
                        'zerolinecolor': 'black',
                        'showline': True,
                        'linewidth': 2,
                        'ticks': "inside",
                        'mirror': 'all',
                        'linecolor': 'black',
                        'gridcolor': 'rgb(200, 200, 200)',
                        # 'nticks': 15,
                        'title': {'text': "Relative Performance",'font': {'size': 18} },
                        'ticksuffix': "%",
                    },
                    'xaxis': {
                        'range': [0, xs[-1]],
                        'zeroline': True,
                        'zerolinewidth': 1,
                        'zerolinecolor': 'black',
                        'gridcolor': 'rgb(200, 200, 200)',
                        'linecolor': 'black',
                        'showline': True,
                        'title': {'text': "#Bounds Check Reintroduced", 'font': {'size': 18}},
                        'linewidth': 2,
                        'mirror': 'all',
                    },
                    'font': {'family': 'Helvetica', 'color': "Black"},
                    'plot_bgcolor': 'white',
                    'autosize': False,
                    'width': 500,
                    'height': height}
    })

    fig.update_xaxes(title_standoff = 1, tickfont=dict(size=16)) # title_font = {"size": 28},)
    fig.update_yaxes(title_standoff = 1,  tickfont=dict(size=16))
    fig.update_layout(legend = dict(font=dict(size = 20)))

    return fig

def getOneBenchmarkFig(benchmark, show_legend=False, show_title=False):
    xs, ys = app._resultProvider.getPhase2Pairs(benchmark)

    color = '#0429A1'
    shape = 0

    scatter_list = []
    if xs is None or ys is None:
        return None
    
    scatter_list.append(go.Scatter(x=xs, y=ys, line={'color': color},
                                   marker={"symbol": shape,
                                           "size": 6, 'opacity': 1},
                                   mode='lines+markers',
                                   name=benchmark, showlegend=show_legend))
    # Set tick suffix
    height = 350

    fig = go.Figure({
        'data': scatter_list,
        'layout': {
                    'legend': {'orientation': 'h', 'x': -0.05, 'y': 2.5},
                    'yaxis': {
                        'zeroline': True,
                        'zerolinewidth': 1,
                        'zerolinecolor': 'black',
                        'showline': True,
                        'linewidth': 2,
                        'ticks': "inside",
                        'mirror': 'all',
                        'linecolor': 'black',
                        'gridcolor': 'rgb(200, 200, 200)',
                        # 'nticks': 15,
                        'title': {'text': "Speedup",'font': {'size': 18} },
                        'ticksuffix': "%",
                    },
                    'xaxis': {
                        'range': [0, xs[-1]],
                        'zeroline': True,
                        'zerolinewidth': 1,
                        'zerolinecolor': 'black',
                        'gridcolor': 'rgb(200, 200, 200)',
                        'linecolor': 'black',
                        'showline': True,
                        'title': {'text': "#Functions with Bounds Check Removed", 'font': {'size': 18}},
                        'linewidth': 2,
                        'mirror': 'all',
                    },
                    'font': {'family': 'Helvetica', 'color': "Black"},
                    'plot_bgcolor': 'white',
                    'autosize': False,
                    'width': 500,
                    'height': height}
    })

    fig.update_xaxes(title_standoff = 1) # title_font = {"size": 28},)
    fig.update_yaxes(title_standoff = 1)

    return fig


@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    if not pathname:
        return 404

    if pathname == '/':
        pathname = '/plots'

    if pathname == '/bar':
        layout = getPlotBarLayout()
        return layout

    if pathname == '/plots':
        layout = getPlotMainLayout()
        return layout
    else:
        return 404
    # You could also return a 404 "URL not found" page here


def genFigs():
    # for benchmark in BENCHMARK_LIST:
        # fig = getOneBenchmarkFig(benchmark, False, False)
        # if not fig:
            # continue
        # print("Generating: " + benchmark)
        # fig.update_layout(showlegend=False, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
        # fig.update_yaxes(title={"standoff": 4})
        # fig.update_traces(marker={"line": {"width":0}}) # Remove border
        # fig.update_layout(showlegend=False, width=400, height=250, margin=dict(l=2, r=2, t=2, b=2))

        # index = benchmark.rfind('-')
        # if index == -1:
            # filename = benchmark
        # else:
            # filename = benchmark[:benchmark.rindex('-')]
        # filename = filename.replace('_', '-')
        # fig.write_image("images/" + filename  + ".pdf")

    # print("Generating comparison Vec/NoVec")
    # fig = getComparisonFig(["brotli_llvm11_vec_fixed_order", "brotli_llvm11_no_vec_fixed_order"], True, False)
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/comparison-vec-11.pdf")

    # print("Generating comparison LLVM9/11")
    # fig = getComparisonFig(["brotli_llvm11_vec_fixed_order", "brotli_llvm9_vec_fixed_order"], True, False)
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/comparison-llvm.pdf")

    # print("Generating comparison fat/cargo")
    # fig = getComparisonFig(["brotli_llvm11_vec_fixed_order", "brotli_llvm11_vec_cargo_fixed_order"], True, False)
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/comparison-cargo.pdf")

    # print("Generating comparison cargo/vec")
    # fig = getComparisonFig(["brotli_llvm11_vec_cargo_fixed_order", "brotli_llvm11_no_vec_cargo_fixed_order"], True, False)
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/comparison-cargo-vec.pdf")

    # print("Generating comparison cargo run 1/2")
    # fig = getComparisonFig(["brotli_llvm11_vec_cargo_fixed_order", "brotli_llvm11_vec_cargo_fixed_order_2"], True, False)
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/comparison-cargo-run2.pdf")

    # print("Generating comparison cargo vs valgrind")
    # fig = getComparisonFig(["brotli_llvm11_vec_cargo_fixed_order", "brotli_llvm11_vec_cargo_fixed_order_valgrind"], True, False)
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/comparison-cargo-valgrind.pdf")

    # print("Generating comparison cargo vs fixed order")
    # fig = getComparisonFig(["brotli_llvm11_vec_cargo_fixed_order", "brotli_llvm11_vec_cargo"], True, False)
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/comparison-cargo-fixed-order.pdf")

    # print("Generating comparison All")
    # fig = getComparisonFig(BENCHMARK_LIST, True, False)
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/comparison-all.pdf")

    print("Generating comparison random vs ordered")
    fig = getComparisonFig(['brotli_llvm11_explore_raw'], True, False, ["One-Checked", "One-Unchecked", "Hotness", "Random"])
    # fig = getComparisonFig(['brotli_llvm11_final'], True, False, ["One-Checked", "One-Unchecked", "Hotness", "Random"])
    # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    fig.update_yaxes(title={"standoff": 4})
    fig.update_traces(marker={"line": {"width":0}}) # Remove border
    fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    fig.write_image("images/brotli-expand-final.pdf")
    
    # print("Generating comparison paper")
    # fig = getComparisonFig(['brotli_llvm11_final'], True, False, ["Hotness", "Random"])
    # # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/brotli-eva-explore.pdf")
    
    # print("Generating comparison paper")
    # fig = getComparisonFig( True, False, ["Hotness", "Random"])
    # # fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    # fig.update_yaxes(title={"standoff": 4})
    # fig.update_traces(marker={"line": {"width":0}}) # Remove border
    # fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    # fig.write_image("images/cost-eva-explore.pdf")

    # print("Generate bar")
    # fig = getBarFig('brotli_llvm11_vec_cargo_exp')
    # fig.write_image("images/bar-cargo-exp.pdf")



if __name__ == '__main__':
    result_root, gen_figs = parseArgs()
    app._resultProvider = ResultProvider(result_root)
    app._resultProvider.updateResult()

    if gen_figs:
        genFigs()
    else:
        app.layout = html.Div([
            dcc.Location(id='url', refresh=False),
            dcc.Link('Plot for different settings', href='/plots'),
            html.Div(id='page-content')
        ])

        app.run_server(debug=False, host='0.0.0.0', port=8090)

    print(MAX_B_VARIANCE, MAX_T_VARIANCE)
    print(ALL_VARIANCE)
