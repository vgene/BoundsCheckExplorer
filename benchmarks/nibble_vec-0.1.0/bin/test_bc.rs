extern crate nibble_vec;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use nibble_vec::Nibblet;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

fn bench_test(nv: &Nibblet, v:&Vec<u8>, n_iterations:usize){
    for _ in 0..n_iterations {
        for (i, _) in v.iter().enumerate() {
            nv.get(i);
        }
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    let v = vec![243, 2, 3, 251, 5, 6, 7, 8, 255];
    let nv = Nibblet::from(v.clone());

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 1000000000;

    // bench
    bench_test(&nv, &v, n_iterations);

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
