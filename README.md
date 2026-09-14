# wasm-lab

Can a real browser engine run as WebAssembly, small and fast enough for an edge
runtime, without writing a layout engine?

**Yes.** And across 1,406 WPT tests it produces byte-identical results to the
native build.

## What this is

`html2png` — HTML on stdin, PNG on stdout. A WASI command, so one binary runs
under wasmtime, Node, or natively.

```sh
wasmtime run html2png/target/wasm32-wasip1/release/html2png.wasm 900 600 < page.html > page.png
```

```
                         HTML  →  stdin
   ┌────────────────────────▼─────────────────────────┐
   │  html2png.wasm     3.14 MB brotli                │
   │                                                   │
   │   blitz-html    parse      html5ever              │
   │   Stylo         cascade    Firefox's CSS engine   │
   │   Taffy         layout     flexbox · grid · block │
   │   Parley        shape      text, embedded faces   │
   │   blitz-paint   → scene    anyrender commands     │
   │   vello_cpu     rasterise  CPU only               │
   │   png           encode                            │
   └────────────────────────┬─────────────────────────┘
                         PNG  →  stdout
```

Everything in the box is vendored. Ours is ~80 lines of plumbing plus font
registration. That is the point: the engine is not the contribution, the
measurement is.

## The measurement

| | native | wasm |
|---|---|---|
| WPT `css/css-flexbox` tests passed | 1048 / 1406 | 1048 / 1406 |
| subtests passed | 4027 / 5759 | 4027 / 5759 |
| per-test differences | — | **0** |
| per-subtest differences | — | **0** |
| CPU time | 17.7 s | 49.3 s (**2.8x**) |

Same engine, same results, different target. WebAssembly costs conformance
nothing and roughly 2.8x CPU.

Against the baseline it replaces — headless Chrome, ~300 MB and a 5–15 s cold
start on Lambda — this is ~95x smaller and instantiates in 1.93 ms.

## Layout

| path | what |
|---|---|
| `html2png/` | the renderer. HTML → PNG, one WASI command |
| `bench.sh` | size after each squeeze, AOT cost, cold start. **Module-agnostic** |
| `host.mjs` | in-process instantiate + call timing. **Module-agnostic** |
| `compare.py` | score *any* stdin→stdout renderer against Chrome on `pages/` |
| `compete/` | Satori + resvg behind the same contract, for a fair head-to-head |
| `upstream/blitz` | Blitz at `main`, patched to run WPT under WASI |
| `upstream/wpt-tests` | WPT pinned at `5a5b2b591` |
| `repro/` | minimal bug reproductions |
| `CRITERIA.md` | criteria and blind predictions, written **before** the first build |
| `RESULTS.md` | scored against them afterwards, including what was wrong |

`bench.sh` and `host.mjs` do not know what a renderer is. An emulator, a game
and a layout engine all answer the same three questions: how big after each
squeeze, how long to instantiate, how long to run.

## Setup

Fonts and the upstream trees are not committed — the faces used for the
measurements are the macOS system Arial, which cannot be redistributed, and the
upstream checkouts are ~3 GB.

```sh
./setup-fonts.sh        # openly-licensed DejaVu Sans, subset to Latin
./setup-upstream.sh     # Blitz @ 450e576dd, WPT @ 5a5b2b591
```

DejaVu is metrically different from Arial, so `compare.py`'s text-heavy rows
will shift slightly from the numbers below. The wasm-vs-native comparison is
unaffected: both targets use whatever faces are present.

The bug fix and the WASI changes to the WPT runner live in `patches/` — see
`patches/README.md`.

## Reproduce

```sh
# the renderer
cd html2png && cargo build --release --target wasm32-wasip1

# real conformance, both targets
cd upstream/blitz
WPT_DIR=./wpt/tests WPT_OUT=./wpt/out-native cargo run -rp wpt css/css-flexbox
wasmtime run --dir .::/blitz --dir ../wpt-tests::/tests \
  --env WPT_DIR=/tests --env WPT_OUT=/blitz/wpt/out-wasm \
  target/wasm32-wasip1/release/wpt.wasm css/css-flexbox

# cross-renderer comparison
RENDERER="node compete/satori2png.mjs" python compare.py
```

## Honest limits

- Two bugs this found — abspos/`z-index` painting at the wrong origin, and
  collapsed table borders — were **already filed upstream** ([#764], [#504]) and
  better root-caused there. No new contribution.
- `compare.py`'s 14 pages are constructed, not real-world. No images, no
  webfonts, no network.
- A third of the payload is full Arial. A Latin subset is the cheapest win left.
- Satori scoring 0/14 is it being used outside its contract, not a defect. For
  flex-only OG images it is the better tool and it is faster.

[#764]: https://github.com/DioxusLabs/blitz/issues/764
[#504]: https://github.com/DioxusLabs/blitz/issues/504
