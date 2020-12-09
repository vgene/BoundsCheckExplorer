extern crate forpaper;
extern crate rand;

#[no_mangle]
#[inline(never)]
fn unknown_size_bench() {
    let mut app_buf: [u8; 320000] = [0; 320000];
    let mut other_buf: [u8; 320000] = [0; 320000];
    for i in 0..320000 {
        other_buf[i] = rand::random();
    }

    for _ in 0..400 {
        forpaper::unknown_size(&other_buf, &mut app_buf);
    }
}

fn main() {
    unknown_size_bench();
}
