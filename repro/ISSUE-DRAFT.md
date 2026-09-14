# SVG text renders blank wherever system fonts are unavailable (e.g. WASM); `DocumentConfig.font_ctx` does not reach it

## Summary

`<svg><text>` renders nothing in any environment without system fonts. The
documented WASM setup is exactly such an environment.

Blitz has two independent font paths:

| path | used by | configurable via |
|---|---|---|
| `parley::FontContext` | HTML/CSS text | `DocumentConfig.font_ctx` ✅ |
| `usvg::fontdb` | SVG `<text>` | nothing ❌ |

`blitz-dom/src/util.rs`:

```rust
pub(crate) static FONT_DB: LazyLock<Arc<fontdb::Database>> = LazyLock::new(|| {
    let mut db = fontdb::Database::new();
    db.load_system_fonts();
    ...
});
```

It is a private `LazyLock` whose only source is `load_system_fonts()`, so a
caller cannot supply faces to it. `build_single_font_ctx` — whose doc comment
reads *"The standard setup for WASM, where browsers don't expose system
fonts"* — populates the Parley context and has no effect here.

`HOWTO_WASM.md` states *"system fonts aren't available in the browser, so wasm
examples bundle a font at compile time."* Bundling a font fixes HTML text and
leaves SVG text blank, with no error or warning.

## Reproduction

blitz-dom `0.3.0-beta.2`, also reproduced on `main` @ `450e576dd`. Renderer is
blitz-html + blitz-paint + `anyrender_vello_cpu`, with a `font_ctx` built by
`build_single_font_ctx` from three embedded Arial faces.

```html
<!doctype html><meta charset=utf-8>
<body style="margin:0;background:#fff;font:16px Arial">
  <p style="margin:8px">HTML text — uses DocumentConfig.font_ctx</p>
  <svg width="420" height="70" xmlns="http://www.w3.org/2000/svg">
    <text x="8" y="30" font-family="Arial" font-size="22" fill="#000">SVG text</text>
  </svg>
</body>
```

Same binary, two targets, 420x130:

| target | HTML text | SVG text | ink pixels |
| --- | --- | --- | --- |
| host (`aarch64-apple-darwin`) | renders | renders | 5183 |
| `wasm32-wasip1` under wasmtime | renders | **blank** | 1881 |

Isolating just the SVG: native 2117 ink px, wasm **0**.

## Why it also shows up in WPT

Running the WPT runner on both targets and diffing the reports per test
(24,581 tests, 110,757 subtests) gives **zero subtest-level differences** and 17
test-level ones. All 17 are SVG-text tests, and all go native-`FAIL` →
wasm-`PASS` — the wasm side renders no text, which happens to match the
reference. So the failure is currently masked as a pass.

Examples: `css/css-pseudo/svg-text-selection-002.html`,
`css/css-masking/clip-path-svg-content/clip-path-text-001.svg`,
`css/css-text-decor/text-shadow/svg-stroke.html`.

## Suggested fix

Let callers supply the SVG font database — e.g. a `DocumentConfig.svg_font_db`,
or derive it from the faces already registered in `font_ctx` so a single
`build_single_font_ctx` call covers both paths. The latter seems closer to what
users expect, given that helper's stated purpose.

I have this working locally and can open a PR. The shape I tested:
`FONT_DB` becomes a system-font fallback behind an optional supplied database,
plus a public `register_svg_fonts(&[&[u8]])` which also sets the generic
families so `font-family: sans-serif` resolves. One call site changes.

Verified on `wasm32-wasip1`: SVG ink pixels go 0 -> matching the native render
on the repro above. Happy to reshape it if you'd rather thread the faces through
`DocumentConfig` instead.
