# Patches against upstream

`setup-upstream.sh` clones Blitz at `450e576dd`. These apply on top of it:

```sh
cd upstream/blitz
git apply ../../patches/01-blitz-dom-svg-fonts.patch
git apply ../../patches/02-wpt-runner-wasi.patch
```

### 01 — blitz-dom: let callers supply the SVG font database

The bug this repo found. `FONT_DB` is a private `LazyLock` filled only by
`load_system_fonts()`, so SVG `<text>` renders blank wherever system fonts do
not exist — which is exactly the WASM configuration Blitz documents.
`DocumentConfig.font_ctx` configures Parley and never reaches it.

Adds `register_svg_fonts(&[&[u8]])`; `FONT_DB` becomes a fallback behind an
optional supplied database. Measured on the repro: SVG ink pixels go from 0 to
matching the native render.

Filed upstream: https://github.com/DioxusLabs/blitz/issues/897

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
