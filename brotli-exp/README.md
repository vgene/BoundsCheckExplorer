## Run the experiment
### Preparation
1. Run `./create_silesia.sh`, it will download silesia and create a tarball (uncompressed). (depending on the internet speed, might take several minutes)
2. Make sure brotli package is installed by running `pip3 install brotli` in your Python3 environment.
3. Run `python silesia_gen.py` to generate a compressed brotli file. (might take around 1-2 minutes)

## Changes to rust-brotli-decompressor
The original [rust-brotli-decompressor](https://github.com/dropbox/rust-brotli-decompressor)

Differences:

- Remove other unsafe usages, only bounds check related unsafe is in this directory

