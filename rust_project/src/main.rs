#![feature(portable_simd)]

use benchfind::{FindAllViaSimd16, FindAllViaSimd32, FindNeedleInHaystack};
use std::simd::Simd;
use std::simd::cmp::SimdPartialEq;

fn main() {
    // Simple test data
    let haystack = b"hello world\nthis is a test\nwith newlines\n";
    let needle = b'\n';

    println!("Testing SIMD implementations...");

    // Test SIMD16
    let results16: Vec<usize> = FindAllViaSimd16::find_all(needle, haystack).collect();
    println!("SIMD16 results: {:?}", results16);

    // Test SIMD32
    let results32: Vec<usize> = FindAllViaSimd32::find_all(needle, haystack).collect();
    println!("SIMD32 results: {:?}", results32);

    // Also test the core SIMD operations directly
    test_simd_operations();
}

fn test_simd_operations() {
    println!("\nTesting core SIMD operations...");

    // Test with 16 lanes
    let data = [0u8; 16];
    let needle = 42u8;

    let simd_vec = Simd::<u8, 16>::from_array(data);
    let needle_vec = Simd::splat(needle);
    let mask = simd_vec.simd_eq(needle_vec);
    let bitmask = mask.to_bitmask();

    println!("16-lane SIMD bitmask: 0x{:04x}", bitmask);

    // Test with 32 lanes
    let data32 = [0u8; 32];
    let simd_vec32 = Simd::<u8, 32>::from_array(data32);
    let needle_vec32 = Simd::splat(needle);
    let mask32 = simd_vec32.simd_eq(needle_vec32);
    let bitmask32 = mask32.to_bitmask();

    println!("32-lane SIMD bitmask: 0x{:08x}", bitmask32);
}
