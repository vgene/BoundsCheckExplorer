extern crate criterion;
extern crate uint;

use criterion::black_box;
use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;

use uint::{construct_uint, uint_full_mul_reg};

construct_uint! {
	pub struct U512(8);
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

fn bench_test(n_iter: usize) {
	let one = U512([
		8326634216714383706,
		15837136097609390493,
		13004317189126203332,
		7031796866963419685,
		12767554894655550452,
		16333049135534778834,
		140317443000293558,
		598963,
	]);
    for _ in 0..n_iter {
        black_box(one >> 128);
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 15000000;

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
