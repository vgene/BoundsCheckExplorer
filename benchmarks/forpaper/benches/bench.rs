extern crate rand;
extern crate forpaper;
#[macro_use] extern crate bencher;

use bencher::{Bencher, black_box};

fn fixed_size_bench(bencher: &mut Bencher) {
    let mut app_buf: [u8; 320000] = [0; 320000];
    let mut other_buf: [u8; 320000] = [0; 320000];
    for i in 0..320000 {
        other_buf[i] = rand::random();
    }

    bencher.iter(|| {
        black_box(forpaper::fixed_size(&other_buf, &mut app_buf));
    });
}

fn unknown_size_bench(bencher: &mut Bencher) {
    let mut app_buf: [u8; 320000] = [0; 320000];
    let mut other_buf: [u8; 320000] = [0; 320000];
    for i in 0..320000 {
        other_buf[i] = rand::random();
    }

    bencher.iter(|| {
        black_box(forpaper::unknown_size(&other_buf, &mut app_buf));
    });
}

fn perf_mot_bench(bencher: &mut Bencher) {
    let mut app_buf: [u8; 320000] = [0; 320000];
    let mut other_buf: [u8; 320000] = [0; 320000];
    for i in 0..320000 {
        other_buf[i] = rand::random();
    }

    bencher.iter(|| {
        black_box(forpaper::perf_mot(&other_buf, &mut app_buf));
    });
}

fn transformation_bench(bencher: &mut Bencher) {
    let mut app_buf: [u8; 320000] = [0; 320000];
    let mut other_buf: [u8; 320000] = [0; 320000];
    for i in 0..320000 {
        other_buf[i] = rand::random();
    }

    bencher.iter(|| {
        black_box(forpaper::transformation(&other_buf, &mut app_buf));
    });
}

benchmark_group!(benches,
                 fixed_size_bench,
                 unknown_size_bench,
                 perf_mot_bench,
                 transformation_bench);

benchmark_main!(benches);
