TODOs:
- [ ] Try on outils
- [ ] See if inlining can be turned off with LTO

Notes:
- Need to turn off inlining by adding `#[inline(never)]` to the called library function, otherwise LTO will inline the called library function and do huge optimizations
