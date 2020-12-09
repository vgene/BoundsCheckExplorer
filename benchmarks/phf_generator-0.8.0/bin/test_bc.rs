extern crate rand;
extern crate phf_generator;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use rand::distributions::Standard;
use rand::rngs::SmallRng;
use rand::{Rng, SeedableRng};
use phf_generator::generate_hash;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

fn bench_test(n_iter: usize, vec: Vec<u64>) {
    for _ in 0..n_iter {
        generate_hash(&vec);
    }
}

fn gen_vec(len: usize) -> Vec<u64> {
    SmallRng::seed_from_u64(0xAAAAAAAAAAAAAAAA).sample_iter(Standard).take(len).collect()
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    let vec = gen_vec(10);

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 4000;

    // bench
    bench_test(n_iterations, vec);

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
