extern crate geo;
use geo::frechet_distance::FrechetDistance;
use geo::{Coordinate, LineString};

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

fn bench_test(n_iter: usize, ls_a: &LineString::<f32>, ls_b: &LineString::<f32>) {
    for _ in 0..n_iter {
        let _ = ls_a.frechet_distance(&ls_b);
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    let points_a = include!("../src/algorithm/test_fixtures/vw_orig.rs");
    let ls_a = LineString::<f32>(
        points_a
            .iter()
            .map(|e| Coordinate { x: e[0], y: e[1] })
            .collect(),
    );
    let points_b = include!("../src/algorithm/test_fixtures/vw_simplified.rs");
    let ls_b = LineString::<f32>(
        points_b
            .iter()
            .map(|e| Coordinate { x: e[0], y: e[1] })
            .collect(),
    );

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 120;

    // bench
    bench_test(n_iterations, &ls_a, &ls_b);

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
