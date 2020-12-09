//#![feature(test)]

extern crate tracing;
extern crate tracing_subscriber;
extern crate bencher;

use bencher::black_box;
use tracing::{span, Event, Id, Metadata};
use tracing_subscriber::{prelude::*, EnvFilter};

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
    black_box(tracing::subscriber::with_default(EnabledSubscriber.with(filter), || {
        for _ in 0..50000 {
            black_box(tracing::debug!(target: "static_filter", "hi"));
        }
    }))
}

fn main() {
    bench();
}
