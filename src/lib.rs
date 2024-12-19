#![feature(portable_simd)]

use std::simd::cmp::SimdPartialEq;
use std::simd::{self, Simd};


pub fn find_all_iterating<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
    haystack.iter()
        .enumerate()
        .filter(move |(_, &b)| b == needle)
        .map(|(i, _)| i)
}

pub fn find_all_via_u16<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
    let (pfx, body, sfx) = unsafe { haystack.align_to::<u16>() };
    let pfx_i = find_all_iterating(needle, pfx);
    let body_i = body.iter().flat_map(|u| u.to_ne_bytes())
        .enumerate()
        .filter(move |(_, b)| *b == needle)
        .map(|(i, _)| i);
    let sfx_i = find_all_iterating(needle, sfx);

    pfx_i.chain(body_i.map(|i| i+pfx.len())).chain(sfx_i.map(|i| i + pfx.len() + body.len()*2))
}


pub fn find_all_via_u32<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
    let (pfx, body, sfx) = unsafe { haystack.align_to::<u32>() };
    let pfx_i = find_all_iterating(needle, pfx);
    let body_i = body.iter().flat_map(|u| u.to_ne_bytes())
        .enumerate()
        .filter(move |(_, b)| *b == needle)
        .map(|(i, _)| i);
    let sfx_i = find_all_iterating(needle, sfx);

    pfx_i.chain(body_i.map(|i| i+pfx.len())).chain(sfx_i.map(|i| i + pfx.len() + body.len()*4))
}

pub fn find_all_via_u64<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
    let (pfx, body, sfx) = unsafe { haystack.align_to::<u64>() };
    let pfx_i = find_all_iterating(needle, pfx);
    let body_i = body.iter().enumerate().flat_map(|(i, u)| u.to_ne_bytes().map(|b| (i*8, b)))
        .enumerate()
        .filter(move |(_, (_, b))| *b == needle)
        .map(|(j, (i, _))| i+j);
    let sfx_i = find_all_iterating(needle, sfx);

    pfx_i.chain(body_i.map(|i| i+pfx.len())).chain(sfx_i.map(|i| i + pfx.len() + body.len()*8))
}

pub fn find_all_via_simd_16<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
    const LANES: usize = 16;
    let (pfx, body, sfx) = haystack.as_simd::<LANES>();
    let pfx_i = find_all_iterating(needle, pfx);
    let body_i = body.iter().enumerate().flat_map(|(i, vec)| {
        let bit_mask = vec.simd_eq(Simd::splat(b'\n')).to_bitmask();
        BitmaskIterator::new(bit_mask).map(move |j| i*LANES+j)
    }
    );
    let sfx_i = find_all_iterating(needle, sfx);

    pfx_i.chain(body_i.map(|i| i+pfx.len())).chain(sfx_i.map(|i| i + pfx.len() + body.len()*8))
}

pub fn find_all_via_simd_32<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
    const LANES: usize = 32;
    let (pfx, body, sfx) = haystack.as_simd::<LANES>();
    let pfx_i = find_all_iterating(needle, pfx);
    let body_i = body.iter().enumerate().flat_map(|(i, vec)| {
        let bit_mask = vec.simd_eq(Simd::splat(b'\n')).to_bitmask();
        BitmaskIterator::new(bit_mask).map(move |j| i*LANES+j)
    }
    );
    let sfx_i = find_all_iterating(needle, sfx);

    pfx_i.chain(body_i.map(|i| i+pfx.len())).chain(sfx_i.map(|i| i + pfx.len() + body.len()*8))
}

pub fn find_all_via_simd_64<'a>(needle: u8, haystack: &'a [u8]) -> impl Iterator<Item = usize> + 'a {
    const LANES: usize = 64;
    let (pfx, body, sfx) = haystack.as_simd::<LANES>();
    let pfx_i = find_all_iterating(needle, pfx);
    let body_i = body.iter().enumerate().flat_map(|(i, vec)| {
        let bit_mask = vec.simd_eq(Simd::splat(b'\n')).to_bitmask();
        BitmaskIterator::new(bit_mask).map(move |j| i*LANES+j)
    }
    );
    let sfx_i = find_all_iterating(needle, sfx);

    pfx_i.chain(body_i.map(|i| i+pfx.len())).chain(sfx_i.map(|i| i + pfx.len() + body.len()*8))
}


struct BitmaskIterator{ bits: u64, counter: usize }

impl BitmaskIterator {
    fn new(bits: u64) -> Self {
        Self {
            bits, counter: 0
        }
    }
}

impl Iterator for BitmaskIterator {
    type Item = usize;

    fn next(&mut self) -> Option<Self::Item> {
        if self.bits == 0 {
            return None
        }

        let zeros = self.bits.trailing_zeros();
        let pos = self.counter + zeros as usize;
        let discard = zeros + 1;
        self.bits = self.bits >> discard;
        self.counter = pos + 1;
        Some(pos)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        // let result = add(2, 2);
        // assert_eq!(result, 4);
    }
}
