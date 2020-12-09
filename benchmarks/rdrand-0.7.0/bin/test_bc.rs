extern crate rand_core;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use rdrand::RdRand;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

fn bench_test(n_iter: usize, gen: RdRand) {
    for _ in 0..n_iter {
        gen.try_next_u16().unwrap();
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    let mut gen = match rdrand::RdRand::new() {
        Ok(g) => g,
        Err(_) => return,
    };

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 100000;

    // bench
    bench_test(n_iterations, gen);

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
