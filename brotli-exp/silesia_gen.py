import brotli

import random
import string

with open('./silesia.tar', 'rb') as f:
    decoded = f.read()

# with open('ipsum.brotli', 'wb') as f:
with open('silesia-5.brotli', 'wb') as f:
    compressed= brotli.compress(decoded, quality=5)
    f.write(compressed)
