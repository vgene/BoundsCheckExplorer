import brotli

import random
import string

# chars = "".join( [random.choice(string.printable) for i in range(150000000)] )
# 
# with open('ipsum.raw', 'w') as f:
#     f.write(chars)
# 
# decoded=str.encode(chars)

with open('./silesia.tar', 'rb') as f:
    decoded = f.read()

# with open('ipsum.brotli', 'wb') as f:
with open('silesia-5.brotli', 'wb') as f:
    compressed= brotli.compress(decoded, quality=5)
    f.write(compressed)
