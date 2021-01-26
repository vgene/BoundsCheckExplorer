## Code changes
- Remove other unsafe usages, only bounds check related unsafe is in this directory

## Run the experiment
### Preparation
1. Run `./create_silesia.sh`, it will download silesia and create a tarball (uncompressed).
2. Make sure brotli package is installed by `pip install brotli` in the intended Python3 environment.
3. Run `python silesia_gen.py` to generate a compressed brotli file.
