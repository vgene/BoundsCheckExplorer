#[macro_use]
extern crate lazy_static;
use outils::graph::dynconn::{DynamicConnectivity, DynamicWeightedComponent};
use outils::graph::dynconn::hdt::DynamicGraph;
use outils::tree::bst::aaforest::AaForest;
use outils::tree::bst::aatree::AaTree;
use outils::tree::bst::BalancedBinaryForest;
use outils::tree::bst::BinarySearchTree;
use outils::tree::bst::waaforest::WeightedAaForest;
use outils::tree::WeightedTree;
use outils::types::{EmptyWeight, VertexIndex};
use rand::Rng;
use std::collections::BTreeMap;
use std::collections::HashMap;
use std::fmt::Display;
use std::ops::{Add, AddAssign};

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

lazy_static! {
    static ref BIG_INSERT_DELETE_SIZE: usize = 10_000;
    static ref BITBOARD_WEIGHT_LENGTH: usize = 384;
    static ref BIG_INSERT_DELETE_DATE: Vec<usize> = {
        let mut list = Vec::with_capacity(*BIG_INSERT_DELETE_SIZE);
        let mut rng = rand::thread_rng();
        for _ in 0..*BIG_INSERT_DELETE_SIZE {
            list.push(rng.gen::<usize>());
        }
        list
    };
}

#[no_mangle]
#[inline(never)]
fn bench() {
    let mut tree: AaTree<usize, _> = AaTree::new(*BIG_INSERT_DELETE_SIZE);

    let start = now();
    let mut timing_error: bool = false;
    let n_iterations: usize = 50;

    for _ in 0..n_iterations{
        for x in 0..*BIG_INSERT_DELETE_SIZE {
            let key = BIG_INSERT_DELETE_DATE[x];
            tree.insert(key, " ");
        }
        for x in 0..*BIG_INSERT_DELETE_SIZE {
            let key = BIG_INSERT_DELETE_DATE[x];
            tree.remove(&key);
        }
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
