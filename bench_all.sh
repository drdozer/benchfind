#!/bin/bash

# 1. Define an array of target configurations
TARGET_CONFIGS=(
  "default"
  "RUSTFLAGS='-C target-cpu=native' native"
  "RUSTFLAGS='-C target-cpu=x86-64-v2' x86-64-v2"
  "RUSTFLAGS='-C target-cpu=x86-64-v3' x86-64-v3"
  "RUSTFLAGS='-C target-cpu=x86-64-v4' x86-64-v4"
)

# 2. Iterate over this array
for config in "${TARGET_CONFIGS[@]}"; do
  # 3.a. Parse the configuration string
  RUSTFLAGS_VAL=""
  BASELINE_NAME=""

  if [[ "$config" == RUSTFLAGS=* ]]; then
    # Extract RUSTFLAGS and baseline name
    # Example: RUSTFLAGS='-C target-cpu=native' native
    # RUSTFLAGS_VAL will be '-C target-cpu=native' (without the quotes)
    RUSTFLAGS_VAL=$(echo "$config" | sed -E "s/RUSTFLAGS='([^']+)'.*/\1/")
    # BASELINE_NAME will be the last word
    BASELINE_NAME=$(echo "$config" | awk '{print $NF}')
  else
    # The whole string is the baseline name
    BASELINE_NAME="$config"
  fi

  # 3.b. Print a message
  echo "-----------------------------------------------------------------------"
  echo "Processing benchmark configuration: $BASELINE_NAME"
  if [ -n "$RUSTFLAGS_VAL" ]; then
    echo "With RUSTFLAGS: $RUSTFLAGS_VAL"
  else
    echo "With default RUSTFLAGS"
  fi
  echo "-----------------------------------------------------------------------"

  # 3.c. If RUSTFLAGS were extracted, export them. Otherwise, ensure RUSTFLAGS is unset.
  if [ -n "$RUSTFLAGS_VAL" ]; then
    export RUSTFLAGS="$RUSTFLAGS_VAL"
  else
    unset RUSTFLAGS
  fi

  # 3.d. Run cargo bench
  echo "Running: cargo bench -- --save-baseline $BASELINE_NAME"
  if ! cargo bench -- --save-baseline "$BASELINE_NAME"; then
    echo "ERROR: cargo bench failed for $BASELINE_NAME"
    # 3.f. Unset RUSTFLAGS before continuing or exiting
    unset RUSTFLAGS
    continue # or exit 1, depending on desired behavior
  fi

  # 3.e. Run ./check_simd.sh
  echo "Running: ./check_simd.sh $BASELINE_NAME"
  if ! ./check_simd.sh "$BASELINE_NAME"; then
    echo "ERROR: ./check_simd.sh failed for $BASELINE_NAME"
    # 3.f. Unset RUSTFLAGS before continuing or exiting
    unset RUSTFLAGS
    continue # or exit 1
  fi

  # 3.f. Unset RUSTFLAGS to ensure a clean environment for the next iteration
  unset RUSTFLAGS
  echo "" # Add a newline for better readability
done

echo "All benchmark configurations processed."
