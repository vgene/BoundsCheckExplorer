TODOs:
- [ ] Try on outils
- [ ] See if inlining can be turned off with LTO

Notes:
- Need to turn off inlining by adding `#[inline(never)]` to the called library function, otherwise LTO will inline the called library function and do huge optimizations

Benchmarks:
- [x] assume_true | 0.1.0 | unknown_size_bench
- [x] outils | 0.2.0 | aatree_big_random_insert_delete
- [x] itertools | 0.9.0 | permutations_iter
- [ ] nibble-vec | 0.1.0 | nib_get_on_vec_of_9_elements (need to drop!)
- [x] hex | 0.4.2 | faster_hex_encode_fallback
- [ ] fancy-regex | 0.4.1 | run_backtrack_limit
- [x] phf-generator | 0.8.0 | gen_hash_small (param: 10)
- [x] geo | 0.16.0 | frechet_distance_f32
- [x] jpeg-decoder | 0.1.20 | decode_a_512x512_JPEG
- [x] crc-any | 2.3.5  | crc32_update_megabytes
