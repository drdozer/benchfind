#![feature(portable_simd)]

use std::simd::Simd;
use std::simd::cmp::SimdPartialEq;

pub trait FindNeedleInHaystack {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a;
}

pub struct FindAllMemchrCrate;
impl FindNeedleInHaystack for FindAllMemchrCrate {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
        memchr::memchr_iter(needle, haystack)
    }
}

pub struct FindAllIterating;
impl FindNeedleInHaystack for FindAllIterating {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
        haystack
            .iter()
            .enumerate()
            .filter(move |&(_, &b)| b == needle)
            .map(|(i, _)| i)
    }
}

pub struct FindAllViaU16;
impl FindNeedleInHaystack for FindAllViaU16 {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
        const BYTES: usize = 2;
        let (pfx, body, sfx) = unsafe { haystack.align_to::<u16>() };
        let pfx_i = FindAllIterating::find_all(needle, pfx);
        let body_i = body
            .iter()
            .flat_map(|u| u.to_ne_bytes())
            .enumerate()
            .filter(move |(_, b)| *b == needle)
            .map(|(i, _)| i);
        let sfx_i = FindAllIterating::find_all(needle, sfx);

        pfx_i
            .chain(body_i.map(|i| i + pfx.len()))
            .chain(sfx_i.map(|i| i + pfx.len() + body.len() * BYTES))
    }
}

pub struct FindAllViaU32;
impl FindNeedleInHaystack for FindAllViaU32 {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
        let (pfx, body, sfx) = unsafe { haystack.align_to::<u32>() };
        let pfx_i = FindAllIterating::find_all(needle, pfx);
        let body_i = body
            .iter()
            .flat_map(|u| u.to_ne_bytes())
            .enumerate()
            .filter(move |(_, b)| *b == needle)
            .map(|(i, _)| i);
        let sfx_i = FindAllIterating::find_all(needle, sfx);

        pfx_i
            .chain(body_i.map(|i| i + pfx.len()))
            .chain(sfx_i.map(|i| i + pfx.len() + body.len() * 4))
    }
}

pub struct FindAllViaU64;
impl FindNeedleInHaystack for FindAllViaU64 {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
        let (pfx, body, sfx) = unsafe { haystack.align_to::<u64>() };
        let pfx_i = FindAllIterating::find_all(needle, pfx);
        let body_i = body
            .iter()
            .flat_map(|u| u.to_ne_bytes())
            .enumerate()
            .filter(move |(_, b)| *b == needle)
            .map(|(i, _)| i);
        let sfx_i = FindAllIterating::find_all(needle, sfx);

        pfx_i
            .chain(body_i.map(|i| i + pfx.len()))
            .chain(sfx_i.map(|i| i + pfx.len() + body.len() * 8))
    }
}

pub struct FindAllViaSimd16;
impl FindNeedleInHaystack for FindAllViaSimd16 {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
        const LANES: usize = 16;
        let (pfx, body, sfx) = haystack.as_simd::<LANES>();
        let pfx_i = FindAllIterating::find_all(needle, pfx);
        let body_i = body.iter().enumerate().flat_map(move |(i, vec)| {
            let bit_mask = vec.simd_eq(Simd::splat(needle)).to_bitmask();
            BitmaskIterator::new(bit_mask).map(move |j| i * LANES + j)
        });
        let sfx_i = FindAllIterating::find_all(needle, sfx);

        pfx_i
            .chain(body_i.map(|i| i + pfx.len()))
            .chain(sfx_i.map(|i| i + pfx.len() + body.len() * LANES))
    }
}

pub struct FindAllViaSimd32;
impl FindNeedleInHaystack for FindAllViaSimd32 {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
        const LANES: usize = 32;
        let (pfx, body, sfx) = haystack.as_simd::<LANES>();
        let pfx_i = FindAllIterating::find_all(needle, pfx);
        let body_i = body.iter().enumerate().flat_map(move |(i, vec)| {
            let bit_mask = vec.simd_eq(Simd::splat(needle)).to_bitmask();
            BitmaskIterator::new(bit_mask).map(move |j| i * LANES + j)
        });
        let sfx_i = FindAllIterating::find_all(needle, sfx);

        pfx_i
            .chain(body_i.map(|i| i + pfx.len()))
            .chain(sfx_i.map(|i| i + pfx.len() + body.len() * LANES))
    }
}

pub struct FindAllViaSimd64;
impl FindNeedleInHaystack for FindAllViaSimd64 {
    fn find_all<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
        const LANES: usize = 64;
        let (pfx, body, sfx) = haystack.as_simd::<LANES>();
        let pfx_i = FindAllIterating::find_all(needle, pfx);
        let body_i = body.iter().enumerate().flat_map(move |(i, vec)| {
            let bit_mask = vec.simd_eq(Simd::splat(needle)).to_bitmask();
            BitmaskIterator::new(bit_mask).map(move |j| i * LANES + j)
        });
        let sfx_i = FindAllIterating::find_all(needle, sfx);

        pfx_i
            .chain(body_i.map(|i| i + pfx.len()))
            .chain(sfx_i.map(|i| i + pfx.len() + body.len() * LANES))
    }
}

struct BitmaskIterator {
    bits: u64,
}

impl BitmaskIterator {
    fn new(bits: u64) -> Self {
        Self { bits }
    }
}

impl Iterator for BitmaskIterator {
    type Item = usize;

    fn next(&mut self) -> Option<Self::Item> {
        if self.bits == 0 {
            return None;
        }

        let pos = self.bits.trailing_zeros() as usize;
        self.bits &= !(1u64 << pos);
        Some(pos)
    }
}

#[cfg(test)]
mod bitset_tests {
    use super::*;

    #[test]
    fn test_empty_bitmask() {
        let mut iter = BitmaskIterator::new(0);
        assert_eq!(iter.next(), None);
    }

    #[test]
    fn test_single_bit() {
        let mut iter = BitmaskIterator::new(1);
        assert_eq!(iter.next(), Some(0));
        assert_eq!(iter.next(), None);
    }

    #[test]
    fn test_multiple_bits() {
        let mut iter = BitmaskIterator::new(0b1010);
        assert_eq!(iter.next(), Some(1));
        assert_eq!(iter.next(), Some(3));
        assert_eq!(iter.next(), None);
    }

    #[test]
    fn test_all_bits_set() {
        let mut iter = BitmaskIterator::new(u64::MAX);
        for i in 0..64 {
            assert_eq!(iter.next(), Some(i));
        }
        assert_eq!(iter.next(), None);
    }

    #[test]
    fn test_msb_only() {
        let mut iter = BitmaskIterator::new(1 << 63);
        assert_eq!(iter.next(), Some(63));
        assert_eq!(iter.next(), None);
    }
}

#[cfg(test)]
mod haystack_tests {
    use super::*;

    const A_TALE_OF_TWO_CITIES: &str = include_str!("../fixtures/a_tale_of_two_cities.txt");
    const BACILLUS_FASTA: &str = include_str!("../fixtures/bacillus.fasta");
    const BACILLUS_EMBL: &str = include_str!("../fixtures/bacillus.embl");

    const TEST_TEXT: &[u8] = b"one\ntwo\nthree\nfour";
    const TEST_TEXT_EXPECTED: &[usize] = &[3, 7, 13];

    const EMPTY_TEXT: &[u8] = b"";
    const EMPTY_TEXT_EXPECTED: &[usize] = &[];

    const NO_NEWLINES_TEXT: &[u8] = b"abc123";
    const NO_NEWLINES_EXPECTED: &[usize] = &[];

    const CONSECUTIVE_TEXT: &[u8] = b"a\n\nb";
    const CONSECUTIVE_EXPECTED: &[usize] = &[1, 2];

    fn validate_find_all<'a, F: FindNeedleInHaystack>() {
        let actual: Vec<usize> = F::find_all(b'\n', TEST_TEXT).collect();
        assert_eq!(actual, TEST_TEXT_EXPECTED);

        let empty_result: Vec<usize> = F::find_all(b'\n', EMPTY_TEXT).collect();
        assert_eq!(empty_result, EMPTY_TEXT_EXPECTED);

        let no_newlines_result: Vec<usize> = F::find_all(b'\n', NO_NEWLINES_TEXT).collect();
        assert_eq!(no_newlines_result, NO_NEWLINES_EXPECTED);

        let consecutive_result: Vec<usize> = F::find_all(b'\n', CONSECUTIVE_TEXT).collect();
        assert_eq!(consecutive_result, CONSECUTIVE_EXPECTED);
    }

    #[test]
    fn test_find_all_iterating() {
        validate_find_all::<FindAllIterating>();
    }

    #[test]
    fn test_find_all_memchr_crate() {
        validate_find_all::<FindAllMemchrCrate>();
    }

    #[test]
    fn test_find_all_via_u16() {
        validate_find_all::<FindAllViaU16>();
    }

    #[test]
    fn test_find_all_via_u32() {
        validate_find_all::<FindAllViaU32>();
    }

    #[test]
    fn test_find_all_via_u64() {
        validate_find_all::<FindAllViaU64>();
    }

    #[test]
    fn test_find_all_via_simd16() {
        validate_find_all::<FindAllViaSimd16>();
    }

    #[test]
    fn test_find_all_via_simd32() {
        validate_find_all::<FindAllViaSimd32>();
    }

    #[test]
    fn test_find_all_via_simd64() {
        validate_find_all::<FindAllViaSimd64>();
    }

    fn test_against_reference_bacillus_fasta<F: FindNeedleInHaystack>() {
        let truth: Vec<_> = FindAllIterating::find_all(b'\n', BACILLUS_FASTA.as_bytes()).collect();
        let test: Vec<_> = F::find_all(b'\n', BACILLUS_FASTA.as_bytes()).collect();
        assert_eq!(test, truth);
    }

    fn test_against_reference_bacillus_embl<F: FindNeedleInHaystack>() {
        let truth: Vec<_> = FindAllIterating::find_all(b'\n', BACILLUS_EMBL.as_bytes()).collect();
        let test: Vec<_> = F::find_all(b'\n', BACILLUS_EMBL.as_bytes()).collect();
        assert_eq!(test, truth);
    }

    fn test_against_reference_two_cities<F: FindNeedleInHaystack>() {
        let truth: Vec<_> =
            FindAllIterating::find_all(b'\n', A_TALE_OF_TWO_CITIES.as_bytes()).collect();
        let test: Vec<_> = F::find_all(b'\n', A_TALE_OF_TWO_CITIES.as_bytes()).collect();
        assert_eq!(test, truth);
    }

    #[test]
    fn test_u16_against_reference_bacillus_fasta() {
        test_against_reference_bacillus_fasta::<FindAllViaU16>();
    }

    #[test]
    fn test_u16_against_reference_bacillus_embl() {
        test_against_reference_bacillus_embl::<FindAllViaU16>();
    }

    #[test]
    fn test_u16_against_reference_two_cities() {
        test_against_reference_two_cities::<FindAllViaU16>();
    }

    #[test]
    fn test_memchr_crate_against_reference_bacillus_fasta() {
        test_against_reference_bacillus_fasta::<FindAllMemchrCrate>();
    }

    #[test]
    fn test_memchr_crate_against_reference_bacillus_embl() {
        test_against_reference_bacillus_embl::<FindAllMemchrCrate>();
    }

    #[test]
    fn test_memchr_crate_against_reference_two_cities() {
        test_against_reference_two_cities::<FindAllMemchrCrate>();
    }

    #[test]
    fn test_u32_against_reference_bacillus_fasta() {
        test_against_reference_bacillus_fasta::<FindAllViaU32>();
    }

    #[test]
    fn test_u32_against_reference_bacillus_embl() {
        test_against_reference_bacillus_embl::<FindAllViaU32>();
    }

    #[test]
    fn test_u32_against_reference_two_cities() {
        test_against_reference_two_cities::<FindAllViaU32>();
    }

    #[test]
    fn test_u64_against_reference_bacillus_fasta() {
        test_against_reference_bacillus_fasta::<FindAllViaU64>();
    }

    #[test]
    fn test_u64_against_reference_bacillus_embl() {
        test_against_reference_bacillus_embl::<FindAllViaU64>();
    }

    #[test]
    fn test_u64_against_reference_two_cities() {
        test_against_reference_two_cities::<FindAllViaU64>();
    }

    #[test]
    fn test_simd16_against_reference_bacillus_fasta() {
        test_against_reference_bacillus_fasta::<FindAllViaSimd16>();
    }

    #[test]
    fn test_simd16_against_reference_bacillus_embl() {
        test_against_reference_bacillus_embl::<FindAllViaSimd16>();
    }

    #[test]
    fn test_simd16_against_reference_two_cities() {
        test_against_reference_two_cities::<FindAllViaSimd16>();
    }

    #[test]
    fn test_simd32_against_reference_bacillus_fasta() {
        test_against_reference_bacillus_fasta::<FindAllViaSimd32>();
    }

    #[test]
    fn test_simd32_against_reference_bacillus_embl() {
        test_against_reference_bacillus_embl::<FindAllViaSimd32>();
    }

    #[test]
    fn test_simd32_against_reference_two_cities() {
        test_against_reference_two_cities::<FindAllViaSimd32>();
    }

    #[test]
    fn test_simd64_against_reference_bacillus_fasta() {
        test_against_reference_bacillus_fasta::<FindAllViaSimd64>();
    }

    #[test]
    fn test_simd64_against_reference_bacillus_embl() {
        test_against_reference_bacillus_embl::<FindAllViaSimd64>();
    }

    #[test]
    fn test_simd64_against_reference_two_cities() {
        test_against_reference_two_cities::<FindAllViaSimd64>();
    }
}
