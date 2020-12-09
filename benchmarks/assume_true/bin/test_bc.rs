extern crate forpaper;
extern crate rand;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;

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
    let n_iterations: usize = 700;

    for _ in 0..n_iterations {
        forpaper::unknown_size(&other_buf, &mut app_buf);
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
