extern crate itertools;

use itertools::Itertools;
use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use std::ops::Range;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

const PERM_COUNT: usize = 6;

fn bench_test(n_iter: usize) {
    struct NewIterator(Range<usize>);

    impl Iterator for NewIterator {
        type Item = usize;

        fn next(&mut self) -> Option<Self::Item> {
            self.0.next()
        }
    }

    for _ in 0..n_iter {
        for _ in NewIterator(0..PERM_COUNT).permutations(PERM_COUNT) {
        }
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 8000;

    // bench
    bench_test(n_iterations);

    let (total, err) = elapsed(start);
    if err {
        timing_error = true;
    }

    if timing_error {
        let _r = writeln!(&mut io::stderr(), "{:}", "Timing error");
    } else {
        writeln!(&mut io::stderr(), "{:} {:} {:}.{:09}",
        n_iterations as u64,
        "Iterations; Time",
        total.as_secs(),
        total.subsec_nanos());
    }
}

fn main() {
    bench();
}
