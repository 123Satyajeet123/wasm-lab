# How to check any of this yourself

Ordered by how long it takes. Nothing here needs a rebuild — the binaries are
already built.

## 1. Render a page without a browser (5 seconds)

```sh
cd ~/Projects/ai/wasm-lab
echo '<h1 style="font:700 40px Arial">hello</h1><div style="display:grid;
  grid-template-columns:1fr 1fr;gap:10px"><p>grid</p><p>works</p></div>' \
| wasmtime run html2png/target/wasm32-wasip1/release/html2png.wasm 600 200 > /tmp/t.png
open /tmp/t.png
```

That is Stylo, Taffy, Parley and vello_cpu inside one WASI module. No Chrome
process, no GPU, no network.

## 2. The SVG bug, before and after (10 seconds)

```sh
# the released engine — SVG text is blank
wasmtime run html2png/target/wasm32-wasip1/release/html2png.wasm 420 130 \
  < repro/svg-text-blank-on-wasm.html > /tmp/before.png

# our patched engine — SVG text renders
wasmtime run probes/blitz-main/target/wasm32-wasip1/release/blitz-main.wasm 420 130 \
  < repro/svg-text-blank-on-wasm.html > /tmp/after.png

open /tmp/before.png /tmp/after.png
```

Both show the HTML paragraph. Only the second shows the SVG text.
Filed upstream as https://github.com/DioxusLabs/blitz/issues/897

## 3. Size and cold start (30 seconds)

```sh
./bench.sh html2png/target/wasm32-wasip1/release/html2png.wasm
```

`host.mjs` is the other half of the harness, for modules that export callable
functions rather than running as a command:

```sh
node host.mjs probes/taffy-probe/target/wasm32-unknown-unknown/release/taffy_probe.wasm \
     layout_probe 400 300
```

Both are module-agnostic — point them at an emulator or a game later and they
answer the same three questions: how big after each squeeze, how long to
instantiate, how long to run.

## 4. Score a renderer against Chrome (3 minutes)

```sh
.venv/bin/python compare.py                              # our renderer:  8/14
RENDERER="node compete/satori2png.mjs" .venv/bin/python compare.py   # Satori: 0/14
```

Reads `pages/`, screenshots each in headless Chrome, renders each with the
chosen engine, diffs. Writes side-by-sides into `out/`.

## 5. The headline claim: WPT, both targets (≈4 min native, ≈35 min wasm)

```sh
cd upstream/blitz

# native
WPT_DIR=./wpt/tests WPT_OUT=./wpt/out-n cargo run -rp wpt css/css-flexbox

# the same runner, compiled to wasm
wasmtime run -W max-wasm-stack=8388608 \
  --dir .::/blitz --dir ../wpt-tests::/tests \
  --env WPT_DIR=/tests --env WPT_OUT=/blitz/wpt/out-w \
  target/wasm32-wasip1/release/wpt.wasm css/css-flexbox
```

Both print `1048 tests PASSED (74.54%)` and `4027 subtests PASSED`.

To prove it per-test rather than trusting the summary lines:

```sh
cd ~/Projects/ai/wasm-lab
.venv/bin/python aggregate.py
```

Compares the stored full-CSS runs: 30,720 tests, 144,640 subtests, **0
subtest-level differences**, 19 test-level — all SVG, all issue #897.

## 6. The MNIST QR code (1 minute)

```sh
cd ~/Projects/ai/mnist
node verify.mjs          # JS must agree with numpy: 300/300, PASS
open mnist_qr.png        # scan with an iPhone — Safari only, Chrome blocks data: URIs
```

## Rebuilding from scratch

Only needed if you change the Rust. `html2png` takes ~5 min cold, the Blitz
workspace ~3 min.

```sh
cd html2png && cargo build --release --target wasm32-wasip1
cd ../upstream/blitz && cargo build -rp wpt --target wasm32-wasip1
```
