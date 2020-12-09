extern crate faster_hex;
extern crate rustc_hex;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use rustc_hex::{FromHex, ToHex};

const DATA: &[u8] = include_bytes!("../src/lib.rs");

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
    let mut dst = vec![0; DATA.len() * 2];

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 8000;

    // bench
    for _ in 0..n_iterations {
        faster_hex::hex_encode_fallback(DATA, &mut dst);
    }

    let (total, err) = elapsed(start);
    if err {
        timing_error = true;
    }

    if timing_error {
        let _r = writeln!(&mut io::stderr(), "{:}", "Timing error");
    } else {
        writeln!(&mut io::stderr(), "{:} {:} {:}.{:09}",
        "Iterations; Time",
        n_iterations as u64,
        total.as_secs(),
        total.subsec_nanos());
    }
}

fn main() {
    bench();
}
