# Benchmarks to test various ways of scanning a byte-array for a single value

This crate is a benchmark of various ways to scan byte arrays for all occurances of a target character.
It should not be used as production code.
As compilation varies by platform and rustc args, you may get very different results in one context vs another.
Proeed with caution.

## Motivation

Scanning byte arrays is at the core of many tasks in string parsing.
However, I've found that the naive way of doing this using rust iterators does not seem to trigger SIMD instruction generation, at least according to the godbolt compiler explorer.
This results in trash performance, as the alg is bottlenecked by fetching single bytes.

In my most recent Advent of Code, I found that the builtin `.lines()` iterator on string was a significant overhead, which is puzzling.
I had expected such a core method within the standard library to be optimized.
So I wanted to understand what's going on.

## What algs we benchmark

This mini project is a benchmark of various ways to scan byte arrays:

* naive iterator-based enumerate/map/filter chain
* memchr in the standard library
* memchr crate
* iteration fetching bytes via u16, u32, u64
* iteration using SIMD 16, 32, 64 bytes

We also look at a range of workloads:

* Short strings, under 100 chars with one or two newlines
* Source files with ragged line newlines
* FASTA bioinformatics data files, with regularly spaced newlines
* Large text, searching for period (`.`) characters

## Impl note

This crate uses the Rust library safe SIMD operations.
It doesn't directly use any intrinsics or hand-crafted assembly.
We are just trying to understand how fairly normal Rust code performs under this workload,
and perhaps understand how vectorisation kicks in with the compiler, or why it doesn't.
