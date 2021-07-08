- Run valgrind
`valgrind --tool=callgrind ./test_bc silesia-5.brotli`

- Parse valgrind output
`perl callgrind_get_unchecked_parser.perl --auto=yes callgrind.out.* cal.out`

- SourceNader will parse the output and generate the experiment results
`python SourceCorvair.py -r /scratch/ziyangx/BoundsCheckExplorer/brotli-expand -a /u/ziyangx/bounds-check/BoundsCheckExplorer/brotli-exp/silesia-5.brotli -o brotli_llvm11_explore_raw -t 10 -g /scratch/ziyangx/BoundsCheckExplorer/brotli-expand/cal.out`
