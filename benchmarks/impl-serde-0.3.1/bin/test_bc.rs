#![feature(test)]
//extern crate serde_derive;
extern crate serde_json;
extern crate impl_serde;
extern crate uint;
extern crate test;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use test::black_box;
//use criterion::black_box

use impl_serde::*; //impl_uint_serde;
use uint::*;

construct_uint! {
	pub struct U256(4);
}
impl_uint_serde!(U256, 4);

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

fn bench_test(n_iter: usize) {
    let param = r#""0x0""#;
    for _ in 0..n_iter {
        black_box(serde_json::from_str::<U256>(&param));
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 7000000;

    // bench
    bench_test(n_iterations);
    // let param = r#""0x0""#;
    // for _ in 0..n_iterations{
    //     black_box(serde_json::from_str::<U256>(&param));
    // }

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
