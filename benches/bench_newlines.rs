use benchfind::*;
use criterion::{
    black_box, criterion_group, criterion_main, measurement::WallTime, BenchmarkGroup, BenchmarkId,
    Criterion,
};

const A_TALE_OF_TWO_CITIES: &str = include_str!("../fixtures/a_tale_of_two_cities.txt");
const BACILLUS_FASTA: &str = include_str!("../fixtures/bacillus.fasta");
const BACILLUS_EMBL: &str = include_str!("../fixtures/bacillus.embl");

const INPUT_NAMES: [&str; 3] = ["A_TALE_OF_TWO_CITIES", "BACILLUS_FASTA", "BACILLUS_EMBL"];
const INPUT_TEXTS: [&str; 3] = [A_TALE_OF_TWO_CITIES, BACILLUS_FASTA, BACILLUS_EMBL];

fn bench_large_texts(c: &mut Criterion) {
    let mut group = c.benchmark_group("large texts");
    group.measurement_time(std::time::Duration::from_secs(15));
    for (name, text) in INPUT_NAMES.iter().zip(INPUT_TEXTS.iter()) {
        bench_with_finder::<FindAllIterating>(&mut group, stringify!(FindAllIterating), name, text);
        bench_with_finder::<FindAllMemchrCrate>(
            &mut group,
            stringify!(FindAllMemchrCrate),
            name,
            text,
        );
        bench_with_finder::<FindAllViaU16>(&mut group, stringify!(FindAllViaU16), name, text);
        bench_with_finder::<FindAllViaU32>(&mut group, stringify!(FindAllViaU32), name, text);
        bench_with_finder::<FindAllViaU64>(&mut group, stringify!(FindAllViaU64), name, text);
        bench_with_finder::<FindAllViaSimd16>(&mut group, stringify!(FindAllViaSimd16), name, text);
        bench_with_finder::<FindAllViaSimd32>(&mut group, stringify!(FindAllViaSimd32), name, text);
        bench_with_finder::<FindAllViaSimd64>(&mut group, stringify!(FindAllViaSimd64), name, text);
    }
    group.finish();
}

fn bench_with_finder<F: FindNeedleInHaystack>(
    group: &mut BenchmarkGroup<WallTime>,
    bench_name: &str,
    name: &str,
    text: &str,
) {
    group.bench_with_input(BenchmarkId::new(bench_name, name), text, |b, st| {
        b.iter(|| {
            for nl in F::find_all(b'\n', black_box(st.as_bytes())) {
                black_box(nl);
            }
        })
    });
}

fn bench_lines_iterators(c: &mut Criterion) {
    let mut group = c.benchmark_group("lines iterators");
    group.measurement_time(std::time::Duration::from_secs(15));
    for (name, text) in INPUT_NAMES.iter().zip(INPUT_TEXTS.iter()) {
        bench_lines_with_finder::<FindAllIterating>(
            &mut group,
            stringify!(FindAllIterating),
            name,
            text,
        );
        bench_lines_with_finder::<FindAllMemchrCrate>(
            &mut group,
            stringify!(FindAllMemchrCrate),
            name,
            text,
        );
        bench_lines_with_finder::<FindAllViaU16>(&mut group, stringify!(FindAllViaU16), name, text);
        bench_lines_with_finder::<FindAllViaU32>(&mut group, stringify!(FindAllViaU32), name, text);
        bench_lines_with_finder::<FindAllViaU64>(&mut group, stringify!(FindAllViaU64), name, text);
        bench_lines_with_finder::<FindAllViaSimd16>(
            &mut group,
            stringify!(FindAllViaSimd16),
            name,
            text,
        );
        bench_lines_with_finder::<FindAllViaSimd32>(
            &mut group,
            stringify!(FindAllViaSimd32),
            name,
            text,
        );
        bench_lines_with_finder::<FindAllViaSimd64>(
            &mut group,
            stringify!(FindAllViaSimd64),
            name,
            text,
        );
        bench_lines_with_lines(&mut group, "str::lines", name, text);
    }
}

fn bench_lines_with_finder<F: FindNeedleInHaystack>(
    group: &mut BenchmarkGroup<WallTime>,
    bench_name: &str,
    name: &str,
    text: &str,
) {
    group.bench_with_input(BenchmarkId::new(bench_name, name), text, |b, st| {
        b.iter(|| {
            let mut last_line_end = 0;
            for nl in F::find_all(b'\n', black_box(st.as_bytes())) {
                let line = &st[last_line_end..nl];
                last_line_end = nl + 1;
                black_box(line);
            }
        })
    });
}

fn bench_lines_with_lines(
    group: &mut BenchmarkGroup<WallTime>,
    bench_name: &str,
    name: &str,
    text: &str,
) {
    group.bench_with_input(BenchmarkId::new(bench_name, name), text, |b, st| {
        b.iter(|| {
            for line in st.lines() {
                black_box(line);
            }
        })
    });
}

criterion_group!(benches, bench_large_texts, bench_lines_iterators);
criterion_main!(benches);
