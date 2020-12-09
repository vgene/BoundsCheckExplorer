#![feature(test)]
extern crate test;
use test::black_box;
extern crate crc_any;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use std::env;

use crc_any::CRC;

fn bench_test(n_iterations: usize) {
    let mut crc = CRC::crc32();
    let mut bytes = Vec::with_capacity(1000000);

    unsafe {
        bytes.set_len(1000000);
    }

    for _ in 0..n_iterations {
        black_box(crc.digest(&bytes));
        black_box(crc.get_crc());
    }
}

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}


#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    //let counts = get_counts();

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 100;

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
