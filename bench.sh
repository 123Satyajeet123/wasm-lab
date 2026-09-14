#!/usr/bin/env bash
# Measure any .wasm module: size after each squeeze, AOT compile cost, cold start.
# Module-agnostic on purpose — a renderer, an emulator and a game all answer the
# same three questions. Usage: ./bench.sh <module.wasm> [export] [args...]
set -euo pipefail
WASM=$1; shift
EXPORT=${1:-}; [ $# -gt 0 ] && shift || true
NAME=$(basename "$WASM" .wasm)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

size() { printf "%'d" "$(stat -f%z "$1" 2>/dev/null || stat -c%s "$1")"; }

# Exactly the features rustc emits. Not --all-features: that turns on the
# compact-imports encoding, which wasmtime rejects. Not the default set either:
# rustc emits trunc_sat. Fail loudly — a silent fallback would report the
# unoptimised size as if it were optimised.
FEATURES="--enable-bulk-memory --enable-sign-ext --enable-nontrapping-float-to-int"
FEATURES="$FEATURES --enable-mutable-globals --enable-multivalue --enable-reference-types"
if ! wasm-opt -Oz $FEATURES "$WASM" -o "$TMP/opt.wasm" 2>"$TMP/err"; then
  echo "wasm-opt FAILED:" >&2; head -3 "$TMP/err" >&2; exit 1
fi
gzip -9 -c "$TMP/opt.wasm" > "$TMP/opt.gz"
brotli -q 11 -c "$TMP/opt.wasm" > "$TMP/opt.br" 2>/dev/null || cp "$TMP/opt.gz" "$TMP/opt.br"

echo "== $NAME"
printf "  raw          %14s B\n" "$(size "$WASM")"
printf "  wasm-opt -Oz %14s B\n" "$(size "$TMP/opt.wasm")"
printf "  + gzip -9    %14s B\n" "$(size "$TMP/opt.gz")"
printf "  + brotli -11 %14s B  <- what ships\n" "$(size "$TMP/opt.br")"

ms() { python3 -c "import sys;print(f'{(float(sys.argv[2])-float(sys.argv[1]))*1000:.1f}')" "$1" "$2"; }
now() { python3 -c "import time;print(time.perf_counter())"; }

t0=$(now); wasmtime compile "$TMP/opt.wasm" -o "$TMP/opt.cwasm" 2>/dev/null; t1=$(now)
printf "  AOT compile  %14s ms  (build step, paid once)\n" "$(ms "$t0" "$t1")"

if [ -n "$EXPORT" ]; then
  best=""
  for _ in 1 2 3 4 5; do
    t0=$(now)
    wasmtime run --allow-precompiled --invoke "$EXPORT" "$TMP/opt.cwasm" "$@" >/dev/null 2>&1
    t1=$(now); d=$(ms "$t0" "$t1")
    best=$(python3 -c "print(min([x for x in ['$best','$d'] if x]or[0],key=float))")
  done
  printf "  cold+run     %14s ms  (best of 5: process, instantiate, %s)\n" "$best" "$EXPORT"
fi
