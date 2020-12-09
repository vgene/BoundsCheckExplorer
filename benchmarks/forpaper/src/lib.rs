/** Fixed src and dst sizes **/

#[no_mangle]
pub fn fixed_size(src: &[u8; 320000], dst: &mut [u8; 320000]) {
    for i in 0..src.len() {
        dst[i] = src[i];
    }
}

/** Both src and dst sizes unknown **/

#[no_mangle]
pub fn unknown_size(src: &[u8], dst: &mut [u8]) {
    for i in 0..src.len() {
        dst[i] = src[i];
    }
}

/** Performance motivated unsafe on unknown sizes **/

#[no_mangle]
pub fn perf_mot(src: &[u8], dst: &mut [u8]) {
    for i in 0..src.len() {
        unsafe {
            *dst.get_unchecked_mut(i) = *src.get_unchecked(i);
        }
    }
}

/** Effectively what our transformation will do **/

#[no_mangle]
pub fn transformation(src: &[u8], dst: &mut [u8]) {
    if src.len() == dst.len() {
        for i in 0..src.len() {
            dst[i] = src[i]
        }
    } else {
        for i in 0..src.len() {
            dst[i] = src[i]
        }
    }
}
