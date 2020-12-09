extern crate jpeg_decoder;
extern crate criterion;

use criterion::black_box;
use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use jpeg_decoder as jpeg;
use jpeg_decoder::ImageInfo;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

fn read_image(image: &[u8]) -> Vec<u8> {
    jpeg::Decoder::new(black_box(image)).decode().unwrap()
}

fn bench_test(n_iter: usize) {
    for _ in 0..n_iter {
        read_image(include_bytes!("tower.jpg"));
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 50;

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
