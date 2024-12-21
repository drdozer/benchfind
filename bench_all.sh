#!/bin/bash

cargo bench -- --save-baseline default
RUSTFLAGS="-C target-cpu=native" cargo bench -- --save-baseline native
