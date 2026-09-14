# Patches against upstream

`setup-upstream.sh` clones Blitz at `450e576dd`. These apply on top of it:

```sh
cd upstream/blitz
git apply ../../patches/01-blitz-dom-svg-fonts.patch
git apply ../../patches/02-wpt-runner-wasi.patch
```

### 01 - blitz-dom: resolve SVG text through the document's font collection

The bug this repo found. usvg keeps its own `fontdb`, filled by default only
from `load_system_fonts()`, so SVG `<text>` renders blank wherever those do not
exist - which is the WASM configuration Blitz documents.
`DocumentConfig::font_ctx` configured Parley and never reached it.

Hands usvg a `FontResolver` backed by the same Fontique collection HTML text
uses, so `font_ctx` is the only font knob. usvg's database starts empty and the
resolver adds faces on demand.

Measured on `repro/svg-text-blank-on-wasm.html`, with `font_ctx` as the only
font configuration: SVG ink pixels go 0 -> 5183, matching the native render, on
both the host and `wasm32-wasip1`.

Filed as https://github.com/DioxusLabs/blitz/issues/897, PR
https://github.com/DioxusLabs/blitz/pull/898. The first version of that PR added
a second font database; the maintainers asked for the resolver instead, which is
what this patch now is.

### 02 — wpt runner: run under WASI

Three changes, none of them rendering-related, needed to run the WPT runner on
`wasm32-wasip1`:

1. `path::absolute()` on `WPT_DIR` — WASI has no working directory.
2. `env!("CARGO_MANIFEST_DIR")` for the output path — a host path baked at
   compile time. Now overridable with `WPT_OUT`.
3. `get_git_hash()` shells out to `git` — WASI cannot spawn processes. It is
   report metadata, so it degrades to a placeholder rather than aborting a run
   whose results are already computed.

It also pins both targets to the same embedded font faces. Without that, native
picks up system fonts WASM cannot see and the comparison measures font
availability rather than the engine.
