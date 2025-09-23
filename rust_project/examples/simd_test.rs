#![feature(portable_simd)]

use std::simd::{Simd, cmp::SimdPartialEq};

// Prevent inlining to make it easier to find in assembly
#[inline(never)]
pub fn simd16_compare(data: &[u8; 16], needle: u8) -> u16 {
    let simd_data = Simd::<u8, 16>::from_array(*data);
    let needle_vec = Simd::splat(needle);
    let mask = simd_data.simd_eq(needle_vec);
    mask.to_bitmask() as u16
}

#[inline(never)]
pub fn simd32_compare(data: &[u8; 32], needle: u8) -> u32 {
    let simd_data = Simd::<u8, 32>::from_array(*data);
    let needle_vec = Simd::splat(needle);
    let mask = simd_data.simd_eq(needle_vec);
    mask.to_bitmask() as u32
}

#[inline(never)]
pub fn simd64_compare(data: &[u8; 64], needle: u8) -> u64 {
    let simd_data = Simd::<u8, 64>::from_array(*data);
    let needle_vec = Simd::splat(needle);
    let mask = simd_data.simd_eq(needle_vec);
    mask.to_bitmask()
}

fn main() {
    let data16 = [0u8; 16];
    let data32 = [0u8; 32];
    let data64 = [0u8; 64];
    let needle = 42u8;

    println!("SIMD16 result: 0x{:04x}", simd16_compare(&data16, needle));
    println!("SIMD32 result: 0x{:08x}", simd32_compare(&data32, needle));
    println!("SIMD64 result: 0x{:016x}", simd64_compare(&data64, needle));
}
