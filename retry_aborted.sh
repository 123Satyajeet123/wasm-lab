#!/usr/bin/env bash
# Wait for the main chunked pass, then retry whatever aborted, with the larger
# stack. css-grid and css-images contain tests that panic natively too, so those
# are expected to stay aborted; css-inline was purely a stack-depth trap.
set -u
until grep -q "^DONE" /tmp/wasm_chunks.log; do sleep 15; done
cd "$(dirname "$0")/upstream/blitz"
OUT=wpt/out-wasm-chunks
: > /tmp/wasm_retry.log
for dir in $(grep ABORTED /tmp/wasm_chunks.log | awk '{print $2}' | sed 's#css/##'); do
  rm -rf "$OUT/$dir"
  if wasmtime run -W max-wasm-stack=8388608 --dir .::/blitz --dir ../wpt-tests::/tests \
      --env WPT_DIR=/tests --env WPT_OUT="/blitz/$OUT/$dir" --env WPT_REV=450e576dd \
      target/wasm32-wasip1/release/wpt.wasm "css/$dir" > /dev/null 2>&1; then
    echo "recovered css/$dir" >> /tmp/wasm_retry.log
  else
    echo "still-aborts css/$dir" >> /tmp/wasm_retry.log
  fi
done
echo "RETRY-DONE" >> /tmp/wasm_retry.log
