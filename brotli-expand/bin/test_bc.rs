extern crate brotli_decompressor;
extern crate core;
#[macro_use]
extern crate alloc_no_stdlib;

use std::io;
#[cfg(feature="std")]
use std::io::{Read,Write};
use core::cmp;

use core::ops;

use brotli_decompressor::BrotliResult;
use brotli_decompressor::BrotliDecompressStream;
#[cfg(feature="std")]
use brotli_decompressor::{Decompressor, DecompressorWriter};
use brotli_decompressor::BrotliState;
use brotli_decompressor::HuffmanCode;

#[cfg(not(feature="disable-timer"))]
use alloc_no_stdlib::{Allocator, SliceWrapper, SliceWrapperMut};
use std::time::SystemTime;
use std::time::Duration;

use std::fs::File;
use std::path::Path;
use std::env;

const NUM_BENCHMARK_ITERATIONS: usize = 2;

pub struct Rebox<T> {
  b: Box<[T]>,
}
impl<T> From<Vec<T>> for Rebox<T> {
  #[inline(always)]
  fn from(val: Vec<T>) -> Self {
    Rebox::<T>{b:val.into_boxed_slice()}
  }
}
impl<T> core::default::Default for Rebox<T> {
  #[inline(always)]
  fn default() -> Self {
    let v: Vec<T> = Vec::new();
    let b = v.into_boxed_slice();
    Rebox::<T> { b: b }
  }
}

impl<T> ops::Index<usize> for Rebox<T> {
  type Output = T;
  #[inline(always)]
  fn index(&self, index: usize) -> &T {
    &(*self.b)[index]
  }
}

impl<T> ops::IndexMut<usize> for Rebox<T> {
  #[inline(always)]
  fn index_mut(&mut self, index: usize) -> &mut T {
    &mut (*self.b)[index]
  }
}

impl<T> alloc_no_stdlib::SliceWrapper<T> for Rebox<T> {
  #[inline(always)]
  fn slice(&self) -> &[T] {
    &*self.b
  }
}

impl<T> alloc_no_stdlib::SliceWrapperMut<T> for Rebox<T> {
  #[inline(always)]
  fn slice_mut(&mut self) -> &mut [T] {
    &mut *self.b
  }
}
pub struct HeapAllocator<T: core::clone::Clone> {
  pub default_value: T,
}

#[cfg(not(feature="unsafe"))]
impl<T: core::clone::Clone> alloc_no_stdlib::Allocator<T> for HeapAllocator<T> {
  type AllocatedMemory = Rebox<T>;
  fn alloc_cell(self: &mut HeapAllocator<T>, len: usize) -> Rebox<T> {
    let v: Vec<T> = vec![self.default_value.clone();len];
    let b = v.into_boxed_slice();
    Rebox::<T> { b: b }
  }
  fn free_cell(self: &mut HeapAllocator<T>, _data: Rebox<T>) {}
}

#[cfg(feature="unsafe")]
impl<T: core::clone::Clone> alloc_no_stdlib::Allocator<T> for HeapAllocator<T> {
  type AllocatedMemory = Rebox<T>;
  fn alloc_cell(self: &mut HeapAllocator<T>, len: usize) -> Rebox<T> {
    let mut v: Vec<T> = Vec::with_capacity(len);
    unsafe {
      v.set_len(len);
    }
    let b = v.into_boxed_slice();
    Rebox::<T> { b: b }
  }
  fn free_cell(self: &mut HeapAllocator<T>, _data: Rebox<T>) {}
}

struct Buffer {
  data: Vec<u8>,
  read_offset: usize,
}
#[cfg(feature="std")]
struct UnlimitedBuffer {
  data: Vec<u8>,
  read_offset: usize,
}

#[cfg(feature="std")]
impl UnlimitedBuffer {
  pub fn new(buf: &[u8]) -> Self {
    let mut ret = UnlimitedBuffer {
      data: Vec::<u8>::new(),
      read_offset: 0,
    };
    ret.data.extend(buf);
    return ret;
  }
}

#[cfg(feature="std")]
impl io::Read for UnlimitedBuffer {
  fn read(self: &mut Self, buf: &mut [u8]) -> io::Result<usize> {
    let bytes_to_read = cmp::min(buf.len(), self.data.len() - self.read_offset);
    if bytes_to_read > 0 {
      buf[0..bytes_to_read].clone_from_slice(&self.data[self.read_offset..
                                              self.read_offset + bytes_to_read]);
    }
    self.read_offset += bytes_to_read;
    return Ok(bytes_to_read);
  }
}

#[cfg(feature="std")]
impl io::Write for UnlimitedBuffer {
  fn write(self: &mut Self, buf: &[u8]) -> io::Result<usize> {
    self.data.extend(buf);
    return Ok(buf.len());
  }
  fn flush(self: &mut Self) -> io::Result<()> {
    return Ok(());
  }
}

impl Buffer {
  pub fn new(buf: &[u8]) -> Buffer {
    let mut ret = Buffer {
      data: Vec::<u8>::new(),
      read_offset: 0,
    };
    ret.data.extend(buf);
    return ret;
  }
}
impl io::Read for Buffer {
  fn read(self: &mut Self, buf: &mut [u8]) -> io::Result<usize> {
    if self.read_offset == self.data.len() {
      self.read_offset = 0;
    }
    let bytes_to_read = cmp::min(buf.len(), self.data.len() - self.read_offset);
    if bytes_to_read > 0 {
      buf[0..bytes_to_read]
        .clone_from_slice(&self.data[self.read_offset..self.read_offset + bytes_to_read]);
    }
    self.read_offset += bytes_to_read;
    return Ok(bytes_to_read);
  }
}
impl io::Write for Buffer {
  fn write(self: &mut Self, buf: &[u8]) -> io::Result<usize> {
    if self.read_offset == self.data.len() {
      return Ok(buf.len());
    }
    self.data.extend(buf);
    return Ok(buf.len());
  }
  fn flush(self: &mut Self) -> io::Result<()> {
    return Ok(());
  }
}
fn _write_all<OutputType>(w: &mut OutputType, buf: &[u8]) -> Result<(), io::Error>
  where OutputType: io::Write
{
  let mut total_written: usize = 0;
  while total_written < buf.len() {
    match w.write(&buf[total_written..]) {
      Err(e) => {
        match e.kind() {
          io::ErrorKind::Interrupted => continue,
          _ => return Err(e),
        }
      }
      Ok(cur_written) => {
        if cur_written == 0 {
          return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "Write EOF"));
        }
        total_written += cur_written;
      }
    }
  }
  Ok(())
}

fn writeln0<OutputType: Write>(strm: &mut OutputType,
                               data: &str)
                               -> core::result::Result<(), io::Error> {
  writeln!(strm, "{:}", data)
}

fn writeln_time<OutputType: Write>(strm: &mut OutputType,
                                   data: &str,
                                   v0: u64,
                                   v1: u64,
                                   v2: u32)
                                   -> core::result::Result<(), io::Error> {
  writeln!(strm, "{:} {:} {:}.{:09}", v0, data, v1, v2)
}

#[cfg(feature="disable-timer")]
fn now() -> Duration {
  return Duration::new(0, 0);
}
#[cfg(not(feature="disable-timer"))]
fn now() -> SystemTime {
  return SystemTime::now();
}

#[cfg(not(feature="disable-timer"))]
fn elapsed(start: SystemTime) -> (Duration, bool) {
  match start.elapsed() {
    Ok(delta) => return (delta, false),
    _ => return (Duration::new(0, 0), true),
  }
}

#[cfg(feature="disable-timer")]
fn elapsed(_start: Duration) -> (Duration, bool) {
  return (Duration::new(0, 0), true);
}


#[no_mangle]
fn bench() -> Result<(), io::Error> {
    let args: Vec<String> = env::args().collect();
    let filename = &args[1]; 
    let mut file = File::open(&Path::new(&filename)).unwrap();
    
    let mut input_v = Vec::new();
    file.read_to_end(&mut input_v);

    // let input_slice = include_bytes!("../testdata/ipsum.brotli");  //"../testdata/alice29.txt.compressed");
    let input_buffer_limit: usize = 65536; // 1677721600; //65536;
    let output_buffer_limit: usize = 65536; //65536;

    let mut input_slice = Buffer::new(&input_v[..]);
    let mut output = Buffer::new(&[]);

    let mut total = Duration::new(0, 0);
    let mut timing_error: bool = false;
    let r = &mut input_slice;
    let mut w = &mut output;

    let range = NUM_BENCHMARK_ITERATIONS;
    // test for 10000 iterations
    for _i in 0..range{
        let mut brotli_state =
            BrotliState::new(HeapAllocator::<u8> { default_value: 0 },
                HeapAllocator::<u32> { default_value: 0 },
                HeapAllocator::<HuffmanCode> { default_value: HuffmanCode::default() });
        let mut input = brotli_state.alloc_u8.alloc_cell(input_buffer_limit);
        let mut output = brotli_state.alloc_u8.alloc_cell(output_buffer_limit);
        let mut available_out: usize = output.slice().len();

        // let amount = try!(r.read(&mut buf));
        let mut available_in: usize = 0;
        let mut input_offset: usize = 0;
        let mut output_offset: usize = 0;
        let mut result: BrotliResult = BrotliResult::NeedsMoreInput;
        loop {
            match result {
                BrotliResult::NeedsMoreInput => {
                    input_offset = 0;
                    match r.read(input.slice_mut()) {
                        Err(e) => {
                            match e.kind() {
                                io::ErrorKind::Interrupted => continue,
                                _ => panic!("Error {:?}", e),
                            }
                        }
                        Ok(size) => {
                            if size == 0 {
                                panic!("Error {:?}",  "size is 0");
                            }
                            available_in = size;
                        }
                    }
                }
                BrotliResult::NeedsMoreOutput => {
                    try!(_write_all(&mut w, &output.slice()[..output_offset]));
                    output_offset = 0;
                }
                BrotliResult::ResultSuccess => break,
                BrotliResult::ResultFailure => panic!("FAILURE"),
            }
            let mut written: usize = 0;
            let start = now();
            result = BrotliDecompressStream(&mut available_in,
                &mut input_offset,
                &input.slice(),
                &mut available_out,
                &mut output_offset,
                &mut output.slice_mut(),
                &mut written,
                &mut brotli_state);

            let (delta, err) = elapsed(start);
            if err {
                timing_error = true;
            }
            total = total + delta;
            if output_offset != 0 {
                try!(_write_all(&mut w, &output.slice()[..output_offset]));
                output_offset = 0;
                available_out = output.slice().len()
            }
        }
    }

    if timing_error {
        let _r = writeln0(&mut io::stderr(), "Timing error");
    } else {
        let _r = writeln_time(&mut io::stderr(),
        "Iterations; Time",
        range as u64,
        total.as_secs(),
        total.subsec_nanos());
    }

    Ok(())

  // we don't need to compare it's correct
  // assert_eq!(output.data.len(), output_slice.len());
  // assert_eq!(output.data, output_slice)
}

// #[test]
// fn benchmark_alice29() {
//   benchmark_decompressed_input(ALICE29_BR, ALICE29, 65536, 65536);
// }

fn main() {
    bench();
}
