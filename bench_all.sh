#!/bin/bash

cargo bench -- --save-baseline default
./check_simd.sh default
RUSTFLAGS="-C target-cpu=native" cargo bench -- --save-baseline native
./check_simd.sh native
RUSTFLAGS="-C target-cpu=x86-64-v2" cargo bench -- --save-baseline x86-64-v2
./check_simd.sh x86-64-v2
RUSTFLAGS="-C target-cpu=x86-64-v3" cargo bench -- --save-baseline x86-64-v3
./check_simd.sh x86-64-v3
RUSTFLAGS="-C target-cpu=x86-64-v4" cargo bench -- --save-baseline x86-64-v4
./check_simd.sh x86-64-v4
