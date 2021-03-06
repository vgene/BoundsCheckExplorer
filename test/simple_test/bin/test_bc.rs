extern crate rand;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;

#[no_mangle]
pub fn simple_test(src: &[u8], dst: &mut [u8]) {
    // not elided
    for i in 0..src.len() {
        dst[i] = src[i];
    }

    // should be elided?
    if (src.len() <= dst.len()) {
        for i in 0..src.len() {
            dst[i] = src[i];
        }
    }

    // should be elided
    if (dst.len() > 10) {
        dst[9] = src[9];
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
    let mut app_buf: [u8; 320000] = [0; 320000];
    let mut other_buf: [u8; 320000] = [0; 320000];
    for i in 0..320000 {
        other_buf[i] = rand::random();
    }

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 2000;

    for _ in 0..n_iterations {
        simple_test(&other_buf, &mut app_buf);
    }

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
