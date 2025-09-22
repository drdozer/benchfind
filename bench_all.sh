#!/bin/bash

# 1. Define an array of target configurations
TARGET_CONFIGS=(
  "default"
  "RUSTFLAGS='-C target-cpu=native' native"
  "RUSTFLAGS='-C target-cpu=x86-64-v2' x86-64-v2"
  "RUSTFLAGS='-C target-cpu=x86-64-v3' x86-64-v3"
  "RUSTFLAGS='-C target-cpu=x86-64-v4' x86-64-v4"
)

# Function to check if baseline results already exist
check_baseline_exists() {
  local baseline_name="$1"

  # Check if criterion baseline directories exist for both benchmarks
  # We look for a few key result files to ensure the benchmark completed
  local bench_newlines_exists=false
  local bench_csv_exists=false

  # Check for newlines benchmark results
  if [ -d "target/criterion/large texts" ] && \
     [ -d "target/criterion/lines iterators" ]; then
    # Look for at least one complete result set
    if find "target/criterion/large texts" -name "$baseline_name" -type d | head -1 | grep -q "$baseline_name" && \
       find "target/criterion/lines iterators" -name "$baseline_name" -type d | head -1 | grep -q "$baseline_name"; then
      # Verify that actual result files exist (not just empty directories)
      if find "target/criterion/large texts" -path "*/$baseline_name/estimates.json" | head -1 | grep -q "estimates.json" && \
         find "target/criterion/lines iterators" -path "*/$baseline_name/estimates.json" | head -1 | grep -q "estimates.json"; then
        bench_newlines_exists=true
      fi
    fi
  fi

  # Check for CSV benchmark results
  if [ -d "target/criterion/parse full csv nested" ] && \
     [ -d "target/criterion/parse full csv flat" ]; then
    if find "target/criterion/parse full csv nested" -name "$baseline_name" -type d | head -1 | grep -q "$baseline_name" && \
       find "target/criterion/parse full csv flat" -name "$baseline_name" -type d | head -1 | grep -q "$baseline_name"; then
      # Verify that actual result files exist
      if find "target/criterion/parse full csv nested" -path "*/$baseline_name/estimates.json" | head -1 | grep -q "estimates.json" && \
         find "target/criterion/parse full csv flat" -path "*/$baseline_name/estimates.json" | head -1 | grep -q "estimates.json"; then
        bench_csv_exists=true
      fi
    fi
  fi

  if [ "$bench_newlines_exists" = true ] && [ "$bench_csv_exists" = true ]; then
    return 0  # Both benchmarks exist
  else
    return 1  # At least one benchmark is missing
  fi
}

# Function to run benchmark with error handling
run_benchmark_safely() {
  local baseline_name="$1"
  local rustflags_val="$2"

  echo "Running: cargo bench -- --save-baseline $baseline_name"

  # Set RUSTFLAGS if provided
  if [ -n "$rustflags_val" ]; then
    export RUSTFLAGS="$rustflags_val"
  else
    unset RUSTFLAGS
  fi

  # Run the benchmark with timeout and error capture
  local benchmark_output
  local benchmark_exit_code

  # Capture both stdout and stderr, with a reasonable timeout
  if benchmark_output=$(timeout 3600 cargo bench -- --save-baseline "$baseline_name" 2>&1); then
    benchmark_exit_code=0
    echo "Benchmark completed successfully"
  else
    benchmark_exit_code=$?
    echo "Benchmark failed with exit code: $benchmark_exit_code"

    # Check for common failure patterns
    if echo "$benchmark_output" | grep -qi "illegal instruction"; then
      echo "ERROR: Illegal instruction detected - CPU does not support required features for $baseline_name"
      echo "This is expected on CPUs that don't support the target instruction set."
    elif echo "$benchmark_output" | grep -qi "sigill"; then
      echo "ERROR: SIGILL (illegal instruction signal) - CPU incompatible with $baseline_name target"
    elif [ $benchmark_exit_code -eq 124 ]; then
      echo "ERROR: Benchmark timed out after 1 hour"
    else
      echo "ERROR: Benchmark failed for unknown reason"
    fi

    echo "Benchmark output:"
    echo "$benchmark_output"
    echo "--- End of benchmark output ---"
  fi

  # Always unset RUSTFLAGS before returning
  unset RUSTFLAGS
  return $benchmark_exit_code
}

# Function to run SIMD check with error handling
run_simd_check_safely() {
  local baseline_name="$1"

  echo "Running: ./check_simd.sh $baseline_name"

  if ./check_simd.sh "$baseline_name" 2>&1; then
    echo "SIMD check completed successfully"
    return 0
  else
    local simd_exit_code=$?
    echo "ERROR: SIMD check failed with exit code: $simd_exit_code"
    echo "This may indicate compilation issues or unsupported target features."
    return $simd_exit_code
  fi
}

# 2. Track overall results
declare -A results
successful_configs=0
skipped_configs=0
failed_configs=0

echo "Starting benchmark suite..."
echo "This script will skip configurations that already have complete results."
echo "========================================================================"

# 3. Iterate over the configuration array
for config in "${TARGET_CONFIGS[@]}"; do
  # 3.a. Parse the configuration string
  RUSTFLAGS_VAL=""
  BASELINE_NAME=""

  if [[ "$config" == RUSTFLAGS=* ]]; then
    # Extract RUSTFLAGS and baseline name
    RUSTFLAGS_VAL=$(echo "$config" | sed -E "s/RUSTFLAGS='([^']+)'.*/\1/")
    BASELINE_NAME=$(echo "$config" | awk '{print $NF}')
  else
    # The whole string is the baseline name
    BASELINE_NAME="$config"
  fi

  # 3.b. Print a message
  echo ""
  echo "======================================================================="
  echo "Processing benchmark configuration: $BASELINE_NAME"
  if [ -n "$RUSTFLAGS_VAL" ]; then
    echo "With RUSTFLAGS: $RUSTFLAGS_VAL"
  else
    echo "With default RUSTFLAGS"
  fi
  echo "======================================================================="

  # 3.c. Check if results already exist
  if check_baseline_exists "$BASELINE_NAME"; then
    echo "SKIPPED: Complete benchmark results already exist for $BASELINE_NAME"
    results["$BASELINE_NAME"]="SKIPPED"
    ((skipped_configs++))
    continue
  else
    echo "No existing results found for $BASELINE_NAME, proceeding with benchmark..."
  fi

  # 3.d. Run cargo bench with error handling
  if run_benchmark_safely "$BASELINE_NAME" "$RUSTFLAGS_VAL"; then
    echo "Benchmark phase completed successfully for $BASELINE_NAME"

    # 3.e. Run SIMD check
    if run_simd_check_safely "$BASELINE_NAME"; then
      echo "Configuration $BASELINE_NAME completed successfully"
      results["$BASELINE_NAME"]="SUCCESS"
      ((successful_configs++))
    else
      echo "Configuration $BASELINE_NAME completed with SIMD check warnings"
      results["$BASELINE_NAME"]="SUCCESS (SIMD check failed)"
      ((successful_configs++))
    fi
  else
    echo "Configuration $BASELINE_NAME failed during benchmarking"
    results["$BASELINE_NAME"]="FAILED"
    ((failed_configs++))

    # Continue with the next configuration instead of exiting
    continue
  fi

  echo "Configuration $BASELINE_NAME processing complete"
  echo ""
done

# 4. Print final summary
echo ""
echo "======================================================================="
echo "BENCHMARK SUITE SUMMARY"
echo "======================================================================="
echo "Total configurations: ${#TARGET_CONFIGS[@]}"
echo "Successful: $successful_configs"
echo "Skipped: $skipped_configs"
echo "Failed: $failed_configs"
echo ""
echo "Detailed results:"
for config in "${TARGET_CONFIGS[@]}"; do
  if [[ "$config" == RUSTFLAGS=* ]]; then
    BASELINE_NAME=$(echo "$config" | awk '{print $NF}')
  else
    BASELINE_NAME="$config"
  fi

  printf "  %-12s: %s\n" "$BASELINE_NAME" "${results[$BASELINE_NAME]:-UNKNOWN}"
done

echo ""
if [ $failed_configs -gt 0 ]; then
  echo "NOTE: Some configurations failed. This is expected on CPUs that don't"
  echo "      support advanced instruction sets (e.g., x86-64-v4 requiring AVX-512)."
fi

if [ $successful_configs -gt 0 ] || [ $skipped_configs -gt 0 ]; then
  echo "Benchmark suite completed with some successful results."
  exit 0
else
  echo "ERROR: All configurations failed. Please check your system setup."
  exit 1
fi
