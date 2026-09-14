#!/usr/bin/env bash
# Run the WPT suite under wasm one directory at a time.
#
# Two wasm-specific hazards, neither of them a rendering difference:
#
#   1. No unwinding. wasm32 defaults to panic=abort, so the runner's per-test
#      crash isolation (which relies on catch_unwind) does not work and one
#      panicking test kills the whole suite. Chunking bounds that to one dir.
#   2. Small stack. Layout recurses per nesting level; the default wasm stack
#      traps with "call stack exhausted" where native's 8 MB survives. Hence
#      -W max-wasm-stack.
set -u
cd "$(dirname "$0")/upstream/blitz"
OUT=wpt/out-wasm-chunks
rm -rf "$OUT"; mkdir -p "$OUT"
: > /tmp/wasm_chunks.log

for dir in $(ls ../wpt-tests/css); do
  [ -d "../wpt-tests/css/$dir" ] || continue
  if wasmtime run -W max-wasm-stack=8388608 --dir .::/blitz --dir ../wpt-tests::/tests \
      --env WPT_DIR=/tests --env WPT_OUT="/blitz/$OUT/$dir" --env WPT_REV=450e576dd \
      target/wasm32-wasip1/release/wpt.wasm "css/$dir" > /dev/null 2>&1; then
    echo "ok      css/$dir" >> /tmp/wasm_chunks.log
  else
    echo "ABORTED css/$dir" >> /tmp/wasm_chunks.log
  fi
done
echo "DONE" >> /tmp/wasm_chunks.log
