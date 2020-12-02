root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

opt -load ${root_path}/remove-bc-pass/build/install/lib/CAT.so -remove-bc -dce -simplifycfg original.bc -o bcrm.bc

clang -O3 bcrm.bc /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib /u/ziyangx/bounds-check/rust-install/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib -ldl -lpthread -lc -lm -o bcrm.exe

./bcrm.exe | grep "ns/iter"
