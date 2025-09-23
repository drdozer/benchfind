#![feature(portable_simd)]

use benchfind::{FindAllViaSimd16, FindAllViaSimd32, FindAllViaSimd64, FindNeedleInHaystack};
use std::simd::{Simd, cmp::SimdPartialEq};

// Test the actual FindAll SIMD implementations
#[inline(never)]
fn test_simd16_findall(haystack: &[u8], needle: u8) -> Vec<usize> {
    FindAllViaSimd16::find_all(needle, haystack).collect()
}

#[inline(never)]
fn test_simd32_findall(haystack: &[u8], needle: u8) -> Vec<usize> {
    FindAllViaSimd32::find_all(needle, haystack).collect()
}

#[inline(never)]
fn test_simd64_findall(haystack: &[u8], needle: u8) -> Vec<usize> {
    FindAllViaSimd64::find_all(needle, haystack).collect()
}

// Direct SIMD implementation for comparison
#[inline(never)]
fn direct_simd16_search(haystack: &[u8], needle: u8) -> Vec<usize> {
    const LANES: usize = 16;
    let mut results = Vec::new();
    let (prefix, body, suffix) = haystack.as_simd::<LANES>();

    // Handle prefix
    for (i, &byte) in prefix.iter().enumerate() {
        if byte == needle {
            results.push(i);
        }
    }

    // Handle SIMD body
    let prefix_len = prefix.len();
    for (chunk_idx, simd_vec) in body.iter().enumerate() {
        let needle_vec = Simd::splat(needle);
        let mask = simd_vec.simd_eq(needle_vec);
        let bitmask = mask.to_bitmask();

        let mut bits = bitmask;
        while bits != 0 {
            let pos = bits.trailing_zeros() as usize;
            bits &= !(1u64 << pos);
            results.push(prefix_len + chunk_idx * LANES + pos);
        }
    }

    // Handle suffix
    let body_len = body.len() * LANES;
    for (i, &byte) in suffix.iter().enumerate() {
        if byte == needle {
            results.push(prefix_len + body_len + i);
        }
    }

    results
}

#[inline(never)]
fn create_test_data(size: usize, pattern_every: usize, needle: u8) -> Vec<u8> {
    let mut data = vec![0u8; size];
    for i in (pattern_every..size).step_by(pattern_every) {
        data[i] = needle;
    }
    data
}

fn main() {
    let needle = b'\n';

    // Test with different data sizes
    let test_cases = [
        (64, 8),    // Small aligned case
        (128, 16),  // Medium case
        (1024, 32), // Large case
        (2048, 64), // Very large case
    ];

    for (size, pattern_every) in test_cases {
        println!(
            "Testing with {} bytes, pattern every {} bytes:",
            size, pattern_every
        );

        let test_data = create_test_data(size, pattern_every, needle);

        let direct_results = direct_simd16_search(&test_data, needle);
        let simd16_results = test_simd16_findall(&test_data, needle);
        let simd32_results = test_simd32_findall(&test_data, needle);
        let simd64_results = test_simd64_findall(&test_data, needle);

        println!("  Direct SIMD16: {} matches", direct_results.len());
        println!("  FindAll SIMD16: {} matches", simd16_results.len());
        println!("  FindAll SIMD32: {} matches", simd32_results.len());
        println!("  FindAll SIMD64: {} matches", simd64_results.len());

        // Verify correctness
        assert_eq!(
            direct_results, simd16_results,
            "SIMD16 results don't match direct implementation"
        );
        assert_eq!(
            direct_results, simd32_results,
            "SIMD32 results don't match direct implementation"
        );
        assert_eq!(
            direct_results, simd64_results,
            "SIMD64 results don't match direct implementation"
        );

        println!("  ✓ All implementations match\n");
    }

    // Test with real-world-like data
    println!("Testing with newline-separated text:");
    let text_data = b"line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\n";

    let text_results = test_simd16_findall(text_data, b'\n');
    println!(
        "Found {} newlines at positions: {:?}",
        text_results.len(),
        text_results
    );

    // Performance test setup message
    println!("\nTo analyze assembly output, compile with:");
    println!(
        "cargo rustc --example test_findall_simd --release -- --emit asm -C target-cpu=native -C target-feature=+avx2"
    );
}
