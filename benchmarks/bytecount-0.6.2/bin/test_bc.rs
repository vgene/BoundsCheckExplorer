extern crate rand;
extern crate bytecount;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use std::env;
use rand::RngCore;

use bytecount::{
    naive_count_32,
    //count, naive_count, naive_count_32,
    //num_chars, naive_num_chars,
};

fn random_bytes(len: usize) -> Vec<u8> {
    let mut result = vec![0; len];
    rand::thread_rng().fill_bytes(&mut result);
    result
}
/*
static COUNTS : &[usize] = &[0, 10, 20, 30, 40, 50, 60, 70, 80, 90,
    100, 120, 140, 170, 210, 250, 300, 400, 500, 600, 700, 800, 900,
    1000, 1_000, 1_200, 1_400, 1_700, 2_100, 2_500, 3_000, 4_000,
    5_000, 6_000, 7_000, 8_000, 9_000, 10_000, 12_000, 14_000, 17_000,
    21_000, 25_000, 30_000, 100_000, 1_000_000];

fn get_counts() -> Vec<usize> {
    env::var("COUNTS").map(
            |s| s.split(',').map(
            |n| str::parse::<usize>(n).unwrap()).collect())
        .unwrap_or(COUNTS.to_owned())
}
*/
fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

fn bench_test(n_iter: usize, s: &usize) {
    let haystack = random_bytes(*s);
    for _ in 0..n_iter {
        naive_count_32(&haystack, 10);
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    //let counts = get_counts();

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 100000000;

    // bench
    bench_test(n_iterations, &0);

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
