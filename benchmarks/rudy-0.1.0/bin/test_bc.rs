#![feature(test)]
extern crate test;
use test::black_box;

extern crate rudy;
use rudy::rudymap::RudyMap;
use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use std::env;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

fn bench_test(n_iterations: usize, m: &RudyMap<u32, u32>) {
    for _ in 0..n_iterations{
        for i in 1u32..100100 {
            black_box(m.contains_key(i));
        }
    }
}


#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    //let counts = get_counts();
    let mut m = RudyMap::new();

    for i in 1u32..100100 {
        m.insert(i, i);
    }

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 1000;

    // bench
    bench_test(n_iterations, &m);

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
