extern crate prometheus;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use prometheus::{Counter, CounterVec, IntCounter, Opts};
use std::collections::HashMap;
use std::sync::{atomic, Arc};
use std::thread;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

fn bench_test(counter: &IntCounter, n_iterations:usize) {
    for _ in 0..n_iterations {
        counter.inc();
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    let signal_exit = Arc::new(atomic::AtomicBool::new(false));
    let counter = IntCounter::new("foo", "bar").unwrap();

    let thread_handles: Vec<_> = (0..4)
        .map(|_| {
            let signal_exit2 = signal_exit.clone();
            let counter2 = counter.clone();
            thread::spawn(move || {
                while !signal_exit2.load(atomic::Ordering::Relaxed) {
                    // Update counter concurrently as the normal group.
                    counter2.inc();
                }
            })
        })
        .collect();

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 40000000;

    // bench
    bench_test(&counter, n_iterations);

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

    // Wait for accompanying thread to exit.
    signal_exit.store(true, atomic::Ordering::Relaxed);
    for h in thread_handles {
        h.join().unwrap();
    }
}

fn main() {
    bench();
}
