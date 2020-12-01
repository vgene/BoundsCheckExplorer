# make sure it's the remove-bc toolchain
# make sure it's the release version of LLVM 9.0.1

root_path="/u/ziyangx/bounds-check/BoundsCheckExplorer"

RUSTFLAGS="-C no-prepopulate-passes -C passes=name-anon-globals -Cdebuginfo=0 -Cembed-bitcode=yes" cargo rustc --release --bench bench -- --emit=llvm-bc  -Clto=fat

mkdir explore
cp target/release/deps/*.bc original.bc
opt -load ${root_path}/show-fn-names/build/install/lib/CAT.so -show-bc-names -disable-output original.bc > fn.tx

opt -load ${root_path}/remove-bc-pass/build/install/lib/CAT.so -remove-bc -simplifycfg -dce original.bc -o bcrm.bc

