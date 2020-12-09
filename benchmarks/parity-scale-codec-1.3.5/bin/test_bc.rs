use std::{convert::{TryFrom, TryInto}};
use parity_scale_codec::*;

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

fn encode_test<T: TryFrom<u8> + Codec>(vec: &Vec<T>, n_iterations: usize)  where T::Error: std::fmt::Debug{
    for _ in 0..n_iterations {
        vec.encode();
    }
}

#[no_mangle]
#[inline(never)]
fn bench<T: TryFrom<u8> + Codec>() where T::Error: std::fmt::Debug {
    let vec_size = 1638400;
    let vec: Vec<T> = (0..=127u8)
        .cycle()
        .take(vec_size)
        .map(|v| v.try_into().unwrap())
        .collect();

    let vec = vec;

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 30000;

    encode_test(&vec, n_iterations);

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
    bench::<i64>();
}
