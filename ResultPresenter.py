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
import numpy as np
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import pickle 

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


def getComparisonFig(benchmarks, show_legend=False, show_title=False):
    scatter_list = []
    for benchmark in benchmarks:
        xs, ys, top_error, bottom_error = app._resultProvider.getAbsoluteTime(benchmark)

        # color = '#0429A1'
        shape = 0

        if xs is None or ys is None:
            return None
    
        scatter_list.append(go.Scatter(x=xs, y=ys, # line={'color': color},
            error_y=dict(type='data', symmetric=False, array=top_error, color='rgba(5,5,5, 0.3)', arrayminus=bottom_error),
                                       marker={"symbol": shape,
                                               "size": 6, 'opacity': 1},
                                       mode='lines+markers',
                                       name=benchmark, showlegend=show_legend))
        # Set tick suffix
    height = 350

    fig = go.Figure({
        'data': scatter_list,
        'layout': {
                    'legend': {'orientation': 'h', 'x': -0.05, 'y': 1.1},
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
                        'title': {'text': "Time",'font': {'size': 18} },
                        'ticksuffix': "s",
                    },
                    'xaxis': {
                        'range': [0, xs[-1]],
                        'zeroline': True,
                        'zerolinewidth': 1,
                        'zerolinecolor': 'black',
                        'gridcolor': 'rgb(200, 200, 200)',
                        'linecolor': 'black',
                        'showline': True,
                        'title': {'text': "#Bounds Check Removed", 'font': {'size': 18}},
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

    print("Generating comparison All")
    fig = getComparisonFig(['brotli_llvm11_vec_cargo_exp_3'], True, False)
    fig.update_layout(showlegend=True, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
    fig.update_yaxes(title={"standoff": 4})
    fig.update_traces(marker={"line": {"width":0}}) # Remove border
    fig.update_layout(showlegend=True, width=800, height=500, margin=dict(l=2, r=2, t=2, b=2))
    fig.write_image("images/brotli-expand-final.pdf")
    
    print("Generate bar")
    fig = getBarFig('brotli_llvm11_vec_cargo_exp')
    fig.write_image("images/bar-cargo-exp.pdf")



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
