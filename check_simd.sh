#!/bin/bash

# 1. Accept one argument: the target CPU name
TARGET_CPU="$1"
if [ -z "$TARGET_CPU" ]; then
  echo "Error: Target CPU argument is required."
  exit 1
fi

# 2. Define a list of benchmark names
BENCHMARK_NAMES=("bench_csv" "bench_newlines")

# SIMD patterns to search for (case-insensitive)
SIMD_PATTERNS=(
  "xmm"
  "ymm"
  "zmm"
  "movdqa" "vmovdqa"
  "movaps" "vmovaps"
  "paddb" "vpaddb" "paddw" "vpaddw" "paddd" "vpaddd" "paddq" "vpaddq"
  "psubb" "vpsubb" "psubw" "vpsubw" "psubd" "vpsubd" "psubq" "vpsubq"
  "pmullw" "vpmullw" "pmulld" "vpmulld"
  "pand" "vpand"
  "por" "vpor"
  "pxor" "vpxor"
  "pavgb" "vpavgb" "pavgw" "vpavgw"
  "pcmpgtb" "vpcmpgtb" "pcmpgtw" "vpcmpgtw" "pcmpgtd" "vpcmpgtd" "pcmpgtq" "vpcmpgtq"
  "pshufb" "vpshufb"
  "pslldq" "vpslldq" "psllw" "vpsllw" "pslld" "vpslld" "psllq" "vpsllq"
  "psrldq" "vpsrldq" "psrlw" "vpsrlw" "psrld" "vpsrld" "psrlq" "vpsrlq"
)

# Convert array to a single grep pattern
GREP_PATTERN=$(IFS="|"; echo "${SIMD_PATTERNS[*]}")

# Ensure the deps directory exists
mkdir -p target/release/deps

# 3. For each benchmark name in the list
for BENCH_NAME in "${BENCHMARK_NAMES[@]}"; do
  echo "-----------------------------------------------------------------------"
  # 3.a. Print a message
  echo "Checking SIMD for benchmark '$BENCH_NAME' with target '$TARGET_CPU'..."

  # 3.g. Clean up previous assembly files and related artifacts for this specific benchmark
  # This is important to make sure we are analyzing the correct file
  echo "Cleaning up previous artifacts for '$BENCH_NAME'..."
  rm -f "target/release/deps/${BENCH_NAME}"*.s
  rm -f "target/release/deps/${BENCH_NAME}"*.o
  rm -f "target/release/deps/lib${BENCH_NAME}"*.rlib
  rm -f "target/release/deps/lib${BENCH_NAME}"*.rmeta
  # Also clean any files that might have a hash but start with the bench name
  find target/release/deps/ -name "${BENCH_NAME}-*.s" -delete
  find target/release/deps/ -name "${BENCH_NAME}-*.o" -delete
  find target/release/deps/ -name "lib${BENCH_NAME}-*.rlib" -delete
  find target/release/deps/ -name "lib${BENCH_NAME}-*.rmeta" -delete


  # 3.b. Construct the compile command
  COMPILE_CMD="cargo rustc --bench $BENCH_NAME --release -- -C target-cpu=$TARGET_CPU --emit asm"
  echo "Compile command: $COMPILE_CMD"

  # 3.c. Execute the compile command
  if ! $COMPILE_CMD; then
    echo "Error: Compilation failed for benchmark '$BENCH_NAME' with target '$TARGET_CPU'."
    # Attempt to clean up potentially partially generated files
    rm -f "target/release/deps/${BENCH_NAME}"*.s
    continue # Move to the next benchmark
  fi

  # Find the generated assembly file.
  # It usually looks like target/release/deps/<benchmark_name>-<hash>.s
  # We'll take the most recently modified .s file that contains the benchmark name.
  ASM_FILE=$(find target/release/deps/ -name "${BENCH_NAME}*.s" -type f -print0 | xargs -0 ls -t | head -n 1)

  if [ -z "$ASM_FILE" ] || [ ! -f "$ASM_FILE" ]; then
    echo "Error: Could not find generated assembly file for benchmark '$BENCH_NAME'."
    # Attempt to clean up
    rm -f "target/release/deps/${BENCH_NAME}"*.s
    continue
  fi
  echo "Found assembly file: $ASM_FILE"

  # 3.d. Search (grep) the generated assembly file
  echo "Searching for SIMD instructions in $ASM_FILE..."
  if grep -Eiq "$GREP_PATTERN" "$ASM_FILE"; then
    # 3.e. If any of these patterns are found
    echo "SIMD instructions FOUND for benchmark '$BENCH_NAME' with target '$TARGET_CPU'."
  else
    # 3.f. Otherwise
    echo "SIMD instructions NOT FOUND for benchmark '$BENCH_NAME' with target '$TARGET_CPU'."
  fi

  # 3.g. Clean up the generated assembly file (and others to be safe for next run)
  echo "Cleaning up assembly file $ASM_FILE..."
  rm -f "$ASM_FILE"
  # Additional cleanup of other potential artifacts for the current benchmark
  # This was partially done at the beginning of the loop, but an extra check here for the specific file is good.
  # find target/release/deps/ -name "${BENCH_NAME}-*.s" -delete # already deleted by rm -f "$ASM_FILE" if name matches
  find target/release/deps/ -name "${BENCH_NAME}-*.o" -delete
  find target/release/deps/ -name "lib${BENCH_NAME}-*.rlib" -delete
  find target/release/deps/ -name "lib${BENCH_NAME}-*.rmeta" -delete


  echo "-----------------------------------------------------------------------"
done

echo "SIMD check script finished."
