# Vendor test: can an HTML/CSS layout engine run as WASM?

Written **before** installing anything, so the test cannot grade itself afterwards.

## The question

Can we render real HTML+CSS to a raster image from inside a WASM module small and
fast enough for an edge runtime — beating headless Chrome's 5-15s cold start and
~300MB binary — without writing a layout engine ourselves?

## Candidates, named up front so dropping one is visible

| Candidate | What it is | Why it might lose |
|---|---|---|
| **Blitz** (Stylo+Taffy+Parley) | modular Rust HTML/CSS renderer | Stylo is Servo-derived; may not build for wasm32 |
| **Taffy** alone | flexbox/grid layout only | no CSS parsing, no text, no paint |
| **Typst** | Rust, wasm-proven, real layout+PDF | its own markup, not HTML |
| **resvg** | Rust, wasm-proven | SVG only |
| **Satori** (Yoga wasm) | JS, in production at Vercel | flexbox only: no grid, no pseudo-elements, no media queries |
| **Servo** direct | the full engine | heavier than Blitz, same wasm risk |
| **@formepdf/html** | commercial Rust/WASM | closed source, can't learn from or extend |
| headless Chrome | the baseline to beat | 300MB, 5-15s cold start |

## Criteria (adopt per criterion, never wholesale)

1. Compiles to `wasm32-unknown-unknown` or `wasm32-wasip1` at all — binary yes/no
2. Size after `wasm-opt -Oz` + brotli **< 8 MB**
3. Cold start (instantiate + first render) **< 200 ms**
4. Renders text from a **supplied** font — WASM has no system fonts
5. Pixel-match vs Chrome on real pages **>= 60%**

If (1) or (4) fails and can't be fixed in a day, the honest answer is "use Chrome"
and we walk away having spent two days, not a year.

## Blind predictions (recorded before the first build)

1. Blitz will **not** compile clean to wasm32 on the first try. Failure will be in
   a platform dependency — fontconfig/font-kit, mio/tokio, or a Stylo build script.
2. **Fonts are the first real wall.** Parley expects system fonts; WASM has none.
   Text metrics will drift before anything else does.
3. Raw wasm will exceed 8 MB before `wasm-opt`.
4. Taffy alone compiles to wasm trivially and lands under 300 KB.

Scored in RESULTS.md. A prediction that was wrong is the useful kind.
