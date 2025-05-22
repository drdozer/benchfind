# Benchmarks to test various ways of scanning a byte-array for a single value

This crate is a benchmark of various ways to scan byte arrays for all occurances of a target character.
It should not be used as production code.
As compilation varies by platform and rustc args, you may get very different results in one context vs another.
Proeed with caution.

## Motivation

Scanning byte arrays is at the core of many tasks in string parsing.
However, I've found that the naive way of doing this using rust iterators does not seem to trigger **SIMD** instruction generation, at least according to the godbolt compiler explorer.
This results in trash performance, as the alg is bottlenecked by fetching single bytes.
I've tried various compiler flags, but haven't found a way to get SIMD to kick in.

In my most recent Advent of Code, I found that the builtin `.lines()` iterator on string was a significant overhead, which is puzzling.
I had expected such a core method within the standard library to be optimized.
So I wanted to understand what's going on.

## What algs we benchmark

This mini project is a benchmark of various ways to scan byte arrays:

* naive iterator-based enumerate/map/filter chain
* memchr crate
* iteration fetching bytes via u16, u32, u64
* iteration using SIMD 16, 32, 64 bytes

We also look at a range of workloads:

* Finding the newlines in large text files
* Parsing CSV files

## Impl note

This crate uses the Rust library safe SIMD operations.
It doesn't directly use any intrinsics or hand-crafted assembly.
We are just trying to understand how fairly normal Rust code performs under this workload,
and perhaps understand how vectorisation kicks in with the compiler, or why it doesn't.

## Big File Newline Results

I am using three long inputs.
| Name | Description | Size | Newlines |
|-|-|-|-|
| A Tale of Two Cities | The full text of the Dickens novel | 789k | 16k |
| Bacillus subtilis genome (fasta format) | The DNA sequence for Bacillus subtilis | 4.1M | 70k |
| Bacillus subtlist genome (embl format) | The DNA sequence and genome annotatinos for Bacillus subtlis | 11M | 160k |


<div style="background-color: white">

![Benchmark results for A Tale of Two Cities](images/A_TALE_OF_TWO_CITIES.svg)
![Benchmark results for the Bacillus subtilis genome as fasta](images/BACILLUS_FASTA.svg)
![Benchmark results for the Bacillus subtilis genome as embl](images/BACILLUS_EMBL.svg)

</div>

The pattern is consistent.
Memchr performs really well.
The naive iterator-based approach is the very slowest implementation.
The SIMD operation processing 64 bytes at a time is the clear winner.

The approaches that try to load in multiple bytes using a wider unsigned type are a bit hit and miss.
On my machine, it really does not like u16 for some reason. I've seen this in other benchmarks.
Moving data via  u32 and u64 loads is the fastest option, and are fairly comparable, with u64 tending to be slightly faster.

The SIMD solutions get faster the larger the lanes.
I do not know if this is due mainly to loading the data into register, or the `to_bitmask` operation being more efficient with the wider types.


## CSV Parsing

I have a country codes CSV file.
The benchmark parses it using two different strategies.
The nested parser first identifies lines, makes a slice for those, and then identifies commas within those lines.
The flat parser has an iterator for all newlines, and another one for all commas.
It then advances the two iterators by turns, to intereave the searches.

<div style="background-color: white">

![Benchmark results for parsing CSV with the nested parser](images/country_codes_nested.svg)
![Benchmark results for parsing CSV with the flat aprser](images/country_codes_flat.svg)

</div>

These results are completely different between the two parsers.
For the nested parser, memchr is the very clear winner.
For the flat parser, the SIMD64 approach is the fastest.

The nested parser is really unkind to the various search algorithms.
For each line, it makes a new slice, and searches within that.
These slices are likely to be poorly aligned, and may be shorter than the SIMD length.
So it will keep falling back to the slow byte-by-byte search.
The memchr alg seems to be coping with this really well, which is amazing.

The flat parser is faster over-all than the nested parser.
It also shows the SIMD64 approach winning out over memchr by a large margin.
It is extremely kind to SIMD load, as it lets both iterators loop over the entire input data.
And as they are looping in lockstep, the data they process will tend to be the same or neighbouring chunks.
We do see some bi-valued behaviour, for example, in SIMD32, which may be due to SIMD blocks for commas that are entirely before vs overlapping a newline.

## Conclusion

These benchmarks seem to show that the rust compiler, at least in this naive setup, is not working very hard to vectorise byte-scanning algs.
This can be seen by the very large gap between the performance of the naive byte-by-byte approach to SIMD64.
We also find that SIMD64 seems to win over memchr for workloads that are friendly to SIMD, which is surprising.

It would be interesting to systematically explore compiler flags, particularly feature flags, to see if this closes the performance gap.
If you are interested in contributing new benchmark cases, or have a plan for making many different feature-flag builds to compare, please open a github issue or send me a PR.

## Extended Benchmarking and SIMD Detection

The `bench_all.sh` script has been enhanced to benchmark against several specific CPU target microarchitectures in addition to `default` and `native`. These targets are:
- `x86-64-v2`
- `x86-64-v3`
- `x86-64-v4`

These targets allow testing for SIMD (Single Instruction, Multiple Data) auto-vectorization across different instruction set levels (SSE, AVX, AVX2, AVX-512).

### SIMD Instruction Check

After each benchmark run for a specific target, the `check_simd.sh` script is automatically invoked. This script performs the following steps:
1. Compiles the benchmarks (`bench_csv.rs`, `bench_newlines.rs`) for the given target, emitting assembly code.
2. Analyzes the generated assembly for common SIMD instruction mnemonics.
3. Reports whether SIMD instructions were detected for each benchmark and target combination.

This allows for a more automated way to assess if the compiler is leveraging SIMD instructions for different CPU targets.

To run the extended benchmarks and SIMD checks:
```bash
./bench_all.sh
```
The output will include messages from `check_simd.sh` indicating whether SIMD instructions were found for each test case.