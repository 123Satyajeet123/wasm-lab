# Results — can an HTML/CSS engine run as WASM?

Measured 2026-09-14 on M-series macOS, rustc 1.95, wasmtime 48, binaryen 132,
Node 26. Every number below came out of `bench.sh` / `host.mjs` in this repo.

## Verdict

**Yes, and by a wider margin than predicted.** Blitz (Stylo + Taffy + Parley)
compiles to `wasm32-wasip1`, runs standalone in wasmtime and Node, and resolves
real CSS — grid, flexbox, media queries and wrapped text — in **~2 ms**.

## Criteria scorecard

| # | Criterion | Target | Measured | |
|---|---|---|---|---|
| 1 | Compiles to wasm32 | yes/no | both targets build | **PASS** |
| 2 | Size, wasm-opt + brotli | < 8 MB | **1.91 MB** | **PASS** |
| 3 | Cold start | < 200 ms | **1.93 ms** instantiate | **PASS** |
| 4 | Text from a supplied font | yes/no | wraps correctly | **PASS** |
| 5 | Pixel-match vs Chrome | >= 60% | 57% strict / 93% layout | **SPLIT** |

Criterion 5 turned out to be two questions wearing one name. See below.

## The numbers

```
blitz_probe (Stylo CSS + Taffy layout + Parley text + embedded font)
  raw                 6,799,085 B
  wasm-opt -Oz        5,953,566 B
  + gzip -9           2,481,502 B
  + brotli -11        1,908,857 B   <- what ships
  compile                  12.4 ms  (cacheable)
  instantiate               1.93 ms (median of 20)
  full layout pass          2.45 ms

taffy_probe (layout only, no CSS parsing, no text)
  brotli -11             74,398 B
  instantiate              0.03 ms
```

Against the baseline it replaces: headless Chrome is ~300 MB with a 5-15 s cold
start on Lambda. This is **~160x smaller** and cold-starts **~1000x faster**.

## Proof the CSS is real, not stubbed

```
layout_height(800,600) -> 69     3-column grid
layout_height(390,844) -> 137    @media (max-width:400px) fires, stacks to 1 column

text_height by viewport width:
  1200->56  800->80  600->80  400->104  300->152  200->176
```

Height grows monotonically as the viewport narrows. That is real line breaking
with real glyph advances — the check that catches a font stack that silently
measures every string as zero.

## Blind predictions, scored

Recorded in CRITERIA.md before the first build. **Three of four were wrong**,
which is the point of writing them down.

| # | Prediction | Outcome |
|---|---|---|
| 1 | Blitz won't compile clean to wasm32 | **WRONG** — 259 crates, clean, 1m44s |
| 2 | Fonts are the first wall | **HALF RIGHT** — a real wall, but not first |
| 3 | Raw wasm exceeds 8 MB | **WRONG** — 6.0 MB raw, 1.55 MB brotli |
| 4 | Taffy compiles trivially, < 300 KB | **RIGHT** — 250 KB raw, 74 KB brotli |

## What actually went wrong, in order

1. **Host assumptions, not platform rot.** `wasm32-unknown-unknown` built fine but
   refused to instantiate: `unknown import: __wbindgen_object_drop_ref`. Traced to
   exactly one shallow crate — `web-time`, an `Instant` shim — pulled by
   `blitz-dom`. It needs a JS host. Building `wasm32-wasip1` instead sidesteps it
   entirely, because there `web-time` falls through to real `std::time`.

2. **Text silently measured as zero.** Layout "worked" and returned plausible
   numbers while every string had zero width. Only the vary-the-width check
   exposed it: 16 px at every viewport from 1200 down to 200. The fix is one
   line — `build_single_font_ctx(FONT)` — whose own doc comment reads *"the
   standard setup for WASM, where browsers don't expose system fonts."* Blitz had
   already solved it; we just had not read far enough.

3. **Two of our own tools lied before the subject did.** `wasm-opt` failed on
   rustc's `trunc_sat` and `bench.sh` silently fell back to copying the input,
   reporting the unoptimised size as optimised. Then `--all-features` "fixed" it
   by emitting a compact-imports encoding wasmtime rejects. The right flag set is
   narrow and explicit, and the fallback now fails loudly.

## Criterion 5: paint, measured

`html2png` is a WASI command — HTML on stdin, PNG on stdout — wrapping
blitz-paint over the `anyrender_vello_cpu` rasteriser. 12.4 MB raw wasm.
It runs identically under wasmtime, Node and natively.

**The wasm and native builds are byte-identical: 0 differing pixels.** Whatever
else is true, the target is not the source of error.

14 feature-partitioned pages, rendered at 900x600 by Chrome 153 headless and by
`html2png.wasm`, Arial pinned in both so the diff measures layout and paint
rather than font choice.

```
feature         exact   within   layout     shift   verdict
block          99.85%   99.90%   99.85%    (0, 0)   PASS
borders        99.13%   99.34%   99.11%    (0, 0)   PASS
flex           99.42%   99.53%   99.64%    (0, 0)   PASS
gradient       78.08%   99.76%   99.56%    (0, 0)   PASS
grid           99.79%   99.85%   99.87%    (0, 0)   PASS
inline         97.80%   98.05%   98.04%    (0, 0)   FAIL
list           99.09%   99.42%   99.31%    (0, 0)   PASS
overflow       98.61%   99.04%   98.62%    (0, 0)   FAIL
position       99.63%   99.70%   99.45%    (0, 0)   PASS
table          97.85%   97.95%   95.40%   (0, -3)   FAIL
text           97.29%   98.29%   98.05%    (0, 0)   FAIL
transform      99.65%   99.80%   99.65%    (0, 0)   PASS
typography     98.54%   98.92%   98.67%    (0, 0)   FAIL
zindex         96.39%   96.40%   95.61%    (6, 6)   FAIL
```

**Strict pass rate 8/14 = 57%. Positional agreement 13/14 = 93%.**

The criterion said ">= 60% pixel-match" and that was under-specified: it bundles
"is the box in the right place" with "does a different rasteriser dither an
identical glyph the same way". Those have different answers. Under the letter of
the criterion this lands at 57% — just under. Under its intent, 13 of 14 pages
put every box exactly where Chrome does. Both numbers are above; the goalposts
were not moved to make either look better.

The `shift` column is what separates them: a uniform translation is a different
bug from scattered disagreement, and only `zindex` shows one.

## Step 1: is the bug ours to report? No.

Tested against Blitz `main` @ 450e576dd (2026-09-13), not just the crates.io
release. **The bug is live on main** — so not a stale-release artifact. But both
of our "real" findings were already filed:

| ours | upstream | |
|---|---|---|
| abspos + `z-index` painted at wrong origin | [#764](https://github.com/DioxusLabs/blitz/issues/764) open 2026-08-23 | root-caused as missing containing-block reparenting in layout-tree construction — our `z-index` case is one manifestation |
| `table` -3px + border differences | [#504](https://github.com/DioxusLabs/blitz/issues/504) open 2026-07-10 | collapsed borders paint a phantom grid from the first cell's border |

No new contribution here, and filing a duplicate would be noise. The harness
detects real bugs — it just found ones better analysed than our own write-up.

Also measured in this step: **native beta.2 scores identically to the wasm build
on all 14 pages, to two decimal places.** Combined with the 0-pixel result, the
wasm target introduces no rendering divergence at all. That is the one number
here nobody else has published.

## The bug this found

An absolutely-positioned element that creates a stacking context is painted at
the wrong origin — the ancestor offset is dropped. Six lines:

```html
<body style="padding:20px">
  <div style="position:relative;height:100px">
    <div style="position:absolute;left:0;top:0;width:30px;height:30px;
                background:#000;z-index:1"></div>
  </div>
</body>

without z-index   Blitz paints (20,20)   matches Chrome
with z-index:1    Blitz paints  (0,0)    ancestor offset lost
```

Three hypotheses were tested and killed before this one held: body padding on
abspos generally (no), auto-width vs fixed-width containing block (no), then
`z-index`. Writing the repro is what stopped a wrong bug report being filed.

## Two errors in the harness, not the subject

1. **One font face.** The first run registered only Arial Regular, so `<th>`,
   `<b>` and `<i>` had nothing to select and the diff blamed Blitz for missing
   weights. Registering bold and italic moved typography 97.26 -> 98.67 and cut
   the table shift from -8px to -3px.
2. **A silent fallback.** `bench.sh` copied its input when `wasm-opt` failed and
   reported the unoptimised size as optimised. A fallback that fabricates a
   plausible number is worse than a crash.

Both were found by checking a number that looked too convenient. Neither was in
the code under test.

## Step 2: the real WPT suite, both targets

The 14 hand-written pages were the wrong tool. Blitz ships a WPT runner
(`wpt/runner`, `just wpt`) and archives results publicly, and WPT already solves
the antialiasing problem we hand-rolled a blur for, via
`<meta name=fuzzy content="maxDifference=15;totalPixels=300">`. So: vendored.

Recipe taken from their own CI (`.github/workflows/wpt.yml`), WPT pinned at
`5a5b2b591` (1.1 GB, 163,029 files), Blitz at `main` 450e576dd.

**The entire WPT runner — rayon, thread-locals and all — compiled to
`wasm32-wasip1` with zero errors.** Three small patches were needed to *run* it
there, none of them rendering-related:

1. `path::absolute()` on `WPT_DIR` — WASI has no working directory.
2. `env!("CARGO_MANIFEST_DIR")` for the output path — a host path baked at
   compile time, meaningless inside the guest. Now `WPT_OUT`.
3. `get_git_hash()` shells out to `git` — WASI cannot spawn processes. It is
   report metadata, so it now degrades to a placeholder instead of aborting a
   run whose results are already computed.

Both targets were forced onto the *same* embedded font faces. Otherwise native
picks up system fonts that WASM cannot see, and the delta would measure font
availability rather than the engine.

### Result: the whole CSS suite

Beyond `css-flexbox`, the full `css` tree was run on both targets — natively in
one pass, and under wasm one directory at a time (see the two hazards below).

```
                            native            wasm
tests compared                         30,720        coverage 90.5%
subtests compared                     144,640
TEST-LEVEL differences                     19
SUBTEST-LEVEL differences                   0
```

**All 19 test-level differences are SVG.** 15 by filename; the remaining four
(`selectors/is-default-ns-003`, `selectors/not-default-ns-003`,
`css-text-decor/text-decoration-propagation-display-contents`,
`css-pseudo/textpath-selection-011`) each contain inline SVG. Every one goes
`FAIL` -> `PASS`, because the wasm side draws no SVG text and accidentally
matches the reference.

So across 144,640 subtests, **every divergence traces to a single unpinned font
database** — the bug documented below. Nothing else differs.

The 9.5% not compared is the five directories that aborted; their causes are
enumerated below and none is a rendering difference.

### Result on css/css-flexbox: zero conformance cost

```
css/css-flexbox              native            wasm
tests RUN                    1406              1406
subtests RUN                 5759              5759
subtests PASSED              4027 (69.93%)     4027 (69.93%)
tests PASSED                 1048 (74.54%)     1048 (74.54%)
tests FAILED                  358               358
```

Summary lines matching is not proof, so the two `wptreport.json` files were
diffed per test and per subtest:

```
tests compared        1406      test-level differences    0
subtests compared     4725      subtest-level differences 0
tests only in one         0
```

**Zero divergence.** Same engine, same results, different target.

### What it costs instead: CPU

```
native   2.63 s wall   17.69 s CPU   736%  (rayon across ~7 cores)
wasm    36.31 s wall   49.27 s CPU   146%
```

Wall-clock is ~13.8x, but that is mostly lost parallelism, not lost speed.
Normalised by CPU time the honest figure is **~2.8x**. Quoting the 13.8x would
be measuring rayon's thread availability and calling it WebAssembly.

### What WASM actually breaks: crash isolation, not rendering

Scaling from one module to the whole CSS suite killed the wasm run at test
~9,000 of 37,503. Not out-of-memory — a panic in grid layout:

```
stylo_taffy::RepetitionWrapper::count  →  unwrap_failed
  in taffy::compute::grid::compute_grid_layout
```

Natively that test is simply recorded `CRASH` and the run continues; the full
native suite reports 4 such tests, one of them literally named
`css/css-grid/firefox-bug-2058181-crash.html`.

**On `wasm32-wasip1` Rust defaults to `panic = abort`.** There is no unwinding,
so the runner's per-test isolation — which relies on `catch_unwind` — cannot
work. A single panicking test aborts the entire suite.

That is the real cost of this target, and it is worth stating precisely because
it is *not* a rendering difference:

- `css/css-flexbox` has **0** crashing tests, so wasm completed it and matched
  native exactly.
- The full `css` suite has **4**, and the first one reached ends the run.

The workaround is to bound the blast radius: `run_wasm_css.sh` runs the suite one
directory at a time, so an abort costs one chunk instead of everything. The
principled fixes are a `panic = unwind` std build for wasm, or one instance per
test — both real work, neither a rendering problem.

### And a second, separate hazard: stack depth

`css/css-inline` aborted for a different reason entirely:

```
wasm trap: call stack exhausted
  taffy::compute::block::compute_block_layout
  blitz_dom::compute_child_layout_internal     ← recursing per nesting level
```

Layout recurses once per level of nesting. Native gets an 8 MB main stack; the
wasm guest gets a far smaller one, so a deeply nested document traps where
native is fine. Confirmed by fixing it:

```
wasmtime run                              → trap: call stack exhausted
wasmtime run -W max-wasm-stack=8388608    → 246/246 tests RUN
```

So the two real costs of this target are **no unwinding** and **a small stack**.
Both are runtime/ABI properties. Neither changes a single pixel.

The chunked run confirms the model exactly. Five of 95 directories aborted:

```
css-grid      panic   native CRASH: firefox-bug-2058181-crash.html
css-images    panic   native CRASH: empty-background-image.html
css-viewport  panic   native CRASH: massive-zoom-viewbox-crash.html
cssom         panic   native CRASH: stylesheet-same-origin.sub.html
css-inline    stack   not a native crash — call stack exhausted
```

Four of five are precisely the four tests the native run reports as `CRASH`,
which is what "no unwinding" predicts: whatever panics natively aborts on wasm.
The fifth is the stack case, and raising the stack recovers it. No other
directory aborted.

## The bug that IS ours: SVG text is silently blank without system fonts

Diffing 24,581 tests produced **0 subtest-level differences** and 17 test-level
ones — every single one an SVG-text test, all native-FAIL to wasm-PASS. That
pattern is not an engine difference; it is a second font path.

```
inline <svg><text>  — native: 2117 ink px     wasm: 0 ink px
```

Root cause, in `blitz-dom/src/util.rs`:

```rust
pub(crate) static FONT_DB: LazyLock<Arc<fontdb::Database>> = LazyLock::new(|| {
    let mut db = fontdb::Database::new();
    db.load_system_fonts();   // the only source, behind a private static
    ...
});
```

`DocumentConfig.font_ctx` — the public font knob, and the one
`build_single_font_ctx` exists to populate — configures **Parley only**. SVG text
goes through this private `usvg` font database, which can be filled *only* from
system fonts. So in any environment without them, SVG text renders blank and
nothing reports an error.

That environment is precisely the one Blitz documents: `HOWTO_WASM.md` says
*"system fonts aren't available in the browser, so wasm examples bundle a
font."* Bundling a font fixes HTML text and does nothing for SVG text.

Searched the tracker: no open or closed issue mentions `fontdb` or SVG fonts.
**Unlike the z-index and table findings, this one appears to be unreported.**
Repro in `repro/svg-text-blank-on-wasm.html`, evidence in `out/svgbug_sbs.png`.

### Fixed, and the fix is tested

Fixed by resolving SVG text through the document's Fontique collection, so
`DocumentConfig::font_ctx` is the only font knob. usvg's own database starts
empty and a `FontResolver` adds faces on demand. (The first attempt added a
second database; the maintainers asked for the resolver, which is better: there
is then nothing to keep in sync.)

```
                              SVG ink pixels
native (system fonts)              5183
wasm, before                       1881   (HTML text only; SVG blank)
wasm, after register_svg_fonts()   5183   matches native
```

Evidence in `out/svgfix_sbs.png`. A draft issue with the repro and a suggested
API shape is in `repro/ISSUE-DRAFT.md` — **not filed**, pending a decision on
whether to send it.

## Step 3: the competitor, measured rather than assumed

No published benchmark compares these, so one was made. `satori2png.mjs` takes
the *same* contract as our renderer — HTML on stdin, PNG on stdout — and the
same 14 pages are scored by the same harness against the same Chrome baseline.

```
                     pass rate   notes
html2png (Blitz)     8/14        5 failures are glyph antialiasing
Satori + resvg       0/14        6 pages hard-error, rest score 0-7%
```

Satori's error is explicit: *"Expected `<div>` to have explicit display: flex,
display: contents, or display: none if it has more than one child node."*

**This is not "Satori is bad".** It is not a CSS engine and does not claim to
be: it renders flex-only templates that you author for it, and it powers
`next/og` doing exactly that, well. Running it over arbitrary HTML is outside
its contract. The 0/14 measures how far apart the two contracts are — and
confirms the ground we are standing on is genuinely unserved, which is what the
vendor test was for.

One structural difference worth noting: `@resvg/resvg-js` ships a
platform-native `.node` binary (`resvgjs.darwin-arm64.node`), so the common
Satori stack is *not* a pure-WASM edge target without swapping to
`@resvg/resvg-wasm`. Ours is one portable module.

```
size, what actually ships
  html2png.wasm         3.14 MB brotli   (12.4 MB raw)
    of which fonts      0.97 MB          31%
    engine alone        2.16 MB
  satori + resvg       ~9.1 MB on disk   (yoga.wasm + harfbuzz.wasm + native .node)

speed, flex page — the only page both render
  html2png (native)     66 ms/page
  satori + resvg        41 ms/page       doing far less work
```

Satori is faster on the one page both can draw, and that is a fair result to
report: for flex-only OG images it is the better tool. The moment a template
uses grid, it stops being a tool at all.

**Cheapest win available:** a third of our payload is full Arial with thousands
of glyphs. A Latin subset would cut most of that ~0.97 MB.

## Step 4: the font win, taken

A third of the payload was full Arial — thousands of glyphs for pages that use
a few dozen. Subsetting to Latin plus common punctuation, arrows and symbols
(`pyftsubset`, layout features kept):

```
fonts        2,077,504 -> 269,184 B    -87%
wasm raw    12,409,050 -> 10,600,728 B
brotli       3,135,473 -> 2,414,266 B   -721 KB, -23%
```

**Rendering is unchanged.** Re-running the full comparison after the swap
reproduces every figure to two decimal places — same 8/14, same percentages,
same shifts. The saving is free, which is the only reason to take it.

## Still open

- `table` keeps a -3px residual with 28% of its disagreement in solid regions:
  a real difference, unexplained.
- `text`, `typography`, `inline`, `overflow` differ only on glyph edges — 1.2%
  of `overflow`'s disagreement is in solid blobs, the rest is antialiasing.
  A different rasteriser will never match Chrome's subpixel positioning, so a
  meaningful text threshold has to be ink-relative, not absolute.
- These are 14 constructed feature pages, not 50 real-world ones. Real pages add
  images, webfonts and network, none of which is tested here.

## Reuse

`bench.sh <module.wasm> [export] [args...]` and `host.mjs` are module-agnostic.
An emulator, a game and a renderer all answer the same three questions: how big
after each squeeze, how long to instantiate, how long to run.
