//#![feature(test)]

//extern crate tracing;
//extern crate tracing_subscriber;
//extern crate bencher;

use criterion::black_box;
use tracing::{span, Event, Id, Metadata};
use tracing_subscriber::{prelude::*, EnvFilter};
use std::time::SystemTime;
use std::time::Duration;
use std::io::Write as IoWrite;
use std::io;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}

struct EnabledSubscriber;

impl tracing::Subscriber for EnabledSubscriber {
    fn new_span(&self, span: &span::Attributes<'_>) -> Id {
        let _ = span;
        Id::from_u64(0xDEAD_FACE)
    }

    fn event(&self, event: &Event<'_>) {
        let _ = event;
    }

    fn record(&self, span: &Id, values: &span::Record<'_>) {
        let _ = (span, values);
    }

    fn record_follows_from(&self, span: &Id, follows: &Id) {
        let _ = (span, follows);
    }

    fn enabled(&self, metadata: &Metadata<'_>) -> bool {
        let _ = metadata;
        true
    }

    fn enter(&self, span: &Id) {
        let _ = span;
    }

    fn exit(&self, span: &Id) {
        let _ = span;
    }
}

#[no_mangle]
#[inline(never)]
fn bench() {
    let filter = "static_filter=info"
        .parse::<EnvFilter>()
        .expect("should parse");

    let start= now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 150000000;

    black_box(tracing::subscriber::with_default(EnabledSubscriber.with(filter), || {
        for _ in 0..n_iterations{
            black_box(tracing::debug!(target: "static_filter", "hi"));
        }
    }));

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
