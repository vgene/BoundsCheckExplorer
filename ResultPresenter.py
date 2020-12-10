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

BENCHMARK_LIST = ["assume_true", "crc-any-2.3.5", "geo-0.16.0", "hex-0.4.2",
                  "jpeg-decoder-0.1.20", "outils-0.2.0",  "phf_generator-0.8.0", "itertools-0.9.0"]
class ResultProvider:

    def __init__(self, path):
        self._path = path
        self._results = None

    def parsePickle(self, root_path):
        results = {}
        for benchmark in BENCHMARK_LIST:
            filename =  root_path + "/" + benchmark+'.pkl'

            if path.isfile(filename):
                with open(filename, 'rb') as fd:
                    d = pickle.load(fd)

                results[benchmark] = d

        self._results = results

    def getPhase2Pairs(self, benchmark):
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


@app.callback(
    dash.dependencies.Output('dd-output-container', 'children'),
    [dash.dependencies.Input('benchmark-dropdown', 'value'), ])
def getOneBenchmarkLayout(benchmark="assume_true"):

    fig = getOneBenchmarkFig(benchmark)

    if fig:
        layout = [html.Div(children='Plot of' + benchmark),
                  dcc.Graph(
            id='bmark-graph',
            figure=fig)]
    else:
        layout = None

    return layout


def getOneBenchmarkFig(benchmark, show_legend=False, show_title=False):
    xs, ys = app._resultProvider.getPhase2Pairs(benchmark)

    color = '#0429A1'
    shape = 0

    scatter_list = []
    if xs is None or ys is None:
        return None
    
    scatter_list.append(go.Scatter(x=xs, y=ys, line={'color': color},
                                   marker={"symbol": shape,
                                           "size": 4, 'opacity': 1},
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
                        'title': {'text': "Speedup"},
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
                        'title': {'text': "#Functions with Bounds Check Removed"},
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

    if pathname == '/plots':
        layout = getPlotMainLayout()
        return layout
    else:
        return 404
    # You could also return a 404 "URL not found" page here


def genFigs():
    for benchmark in BENCHMARK_LIST:
        fig = getOneBenchmarkFig(benchmark, False, False)
        if not fig:
            continue
        print("Generating: " + benchmark)
        fig.update_layout(showlegend=False, height=300, yaxis={"nticks": 6}, xaxis={'nticks': 8})
        fig.update_yaxes(title={"standoff": 1})
        fig.update_traces(marker={"line": {"width":0}}) # Remove border
        fig.update_layout(showlegend=False, width=400, height=250, margin=dict(l=2, r=2, t=2, b=2))

        index = benchmark.rfind('-')
        if index == -1:
            filename = benchmark
        else:
            filename = benchmark[:benchmark.rindex('-')]
        filename = filename.replace('_', '-')
        fig.write_image("images/" + filename  + ".pdf")


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

        app.run_server(debug=False, host='0.0.0.0', port=8070)
