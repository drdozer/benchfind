use benchfind::*;
use criterion::{
    black_box, criterion_group, criterion_main, measurement::WallTime, BenchmarkGroup, BenchmarkId,
    Criterion,
};

const COUNTRY_CODES: &str = include_str!("../fixtures/country_codes.txt");

fn bench_parse_full_nested_csv(c: &mut Criterion) {
    let mut group = c.benchmark_group("parse full csv nested");
    group.measurement_time(std::time::Duration::from_secs(15));

    parse_csv_nested::<FindAllIterating>(&mut group, stringify!(FindAllIterating), COUNTRY_CODES);
    parse_csv_nested::<FindAllMemchrCrate>(
        &mut group,
        stringify!(FindAllMemchrCrate),
        COUNTRY_CODES,
    );
    parse_csv_nested::<FindAllViaU16>(&mut group, stringify!(FindAllViaU16), COUNTRY_CODES);
    parse_csv_nested::<FindAllViaU32>(&mut group, stringify!(FindAllViaU32), COUNTRY_CODES);
    parse_csv_nested::<FindAllViaU64>(&mut group, stringify!(FindAllViaU64), COUNTRY_CODES);
    parse_csv_nested::<FindAllViaSimd16>(&mut group, stringify!(FindAllViaSimd16), COUNTRY_CODES);
    parse_csv_nested::<FindAllViaSimd32>(&mut group, stringify!(FindAllViaSimd32), COUNTRY_CODES);
    parse_csv_nested::<FindAllViaSimd64>(&mut group, stringify!(FindAllViaSimd64), COUNTRY_CODES);
}

fn bench_parse_full_flat_csv(c: &mut Criterion) {
    let mut group = c.benchmark_group("parse full csv flat");
    group.measurement_time(std::time::Duration::from_secs(15));

    parse_csv_flat::<FindAllIterating>(&mut group, stringify!(FindAllIterating), COUNTRY_CODES);
    parse_csv_flat::<FindAllMemchrCrate>(&mut group, stringify!(FindAllMemchrCrate), COUNTRY_CODES);
    parse_csv_flat::<FindAllViaU16>(&mut group, stringify!(FindAllViaU16), COUNTRY_CODES);
    parse_csv_flat::<FindAllViaU32>(&mut group, stringify!(FindAllViaU32), COUNTRY_CODES);
    parse_csv_flat::<FindAllViaU64>(&mut group, stringify!(FindAllViaU64), COUNTRY_CODES);
    parse_csv_flat::<FindAllViaSimd16>(&mut group, stringify!(FindAllViaSimd16), COUNTRY_CODES);
    parse_csv_flat::<FindAllViaSimd32>(&mut group, stringify!(FindAllViaSimd32), COUNTRY_CODES);
    parse_csv_flat::<FindAllViaSimd64>(&mut group, stringify!(FindAllViaSimd64), COUNTRY_CODES);
}

// This is a very bad way to parse a CSV file.
// It doesn't handle escaping, last lines that lack a trailing newline, and has other issues.
// It' just here for benchnarking.
fn parse_csv_nested<F: FindNeedleInHaystack>(
    group: &mut BenchmarkGroup<WallTime>,
    bench_name: &str,
    csv_text: &str,
) {
    group.bench_with_input(
        BenchmarkId::new(bench_name, "nested parsing"),
        csv_text,
        |b, st| {
            b.iter(|| {
                let mut last_line = 0;
                for next_line in F::find_all(b'\n', st.as_bytes()) {
                    let mut last_col = 0;
                    let line = st[last_line..next_line].as_bytes();
                    for next_col in F::find_all(b',', line) {
                        black_box(&line[last_col..next_col]);
                        last_col = next_col;
                    }
                    if last_col > 0 && last_col < line.len() {
                        black_box(&line[last_col..]);
                    }
                    last_line = next_line;
                }
            })
        },
    );
}

// This is a better way to parse a CSV file.
// However, it' just here for benchnarking.
fn parse_csv_flat<F: FindNeedleInHaystack>(
    group: &mut BenchmarkGroup<WallTime>,
    bench_name: &str,
    csv_text: &str,
) {
    group.bench_with_input(
        BenchmarkId::new(bench_name, "flat parsing"),
        csv_text,
        |b, st| {
            b.iter(|| {
                let st = st.as_bytes();
                let mut newlines = F::find_all(b'\n', st);
                let mut commas = F::find_all(b',', st);

                let mut from = 0;
                let mut last_comma = commas.next();
                while let Some(newline) = newlines.next() {
                    while let Some(comma) = last_comma
                        && comma < newline
                    {
                        black_box(&st[from..comma]);
                        from = comma + 1;
                        last_comma = commas.next();
                    }
                    black_box(&st[from..newline]);
                    from = newline + 1;
                }
            })
        },
    );
}

criterion_group!(
    benches,
    bench_parse_full_nested_csv,
    bench_parse_full_flat_csv
);
criterion_main!(benches);
