extern crate fancy_regex;
extern crate regex;

use std::time::SystemTime;
use std::time::Duration;
use std::io;
use std::io::Write as IoWrite;
use fancy_regex::internal::{analyze, compile, run_default};
use fancy_regex::Expr;
use regex::Regex;

fn now() -> SystemTime {
    return SystemTime::now();
}

fn elapsed(start: SystemTime) -> (Duration, bool) {
    match start.elapsed() {
        Ok(delta) => return (delta, false),
        _ => return (Duration::new(0, 0), true),
    }
}
/*
fn bench_test<'a>(n_iter: usize, tree: ExprTree, a: Info<'a>, p: Prog, s: str) {
    for _ in 0..n_iter {
        run_default(&p, &s, 0).unwrap_err();
    }
}
*/
#[no_mangle]
#[inline(never)]
fn bench() {
    // setup
    let tree = Expr::parse_tree("(?i)(a|b|ab)*(?=c)").unwrap();
    let a = analyze(&tree).unwrap();
    let p = compile(&a).unwrap();
    let s = "abababababababababababababababababababababababababababab";

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 5;

    // bench
    for _ in 0..n_iterations {
        run_default(&p, &s, 0).unwrap_err();
    }
    //bench_test(n_iterations, tree, a, p, s);

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
