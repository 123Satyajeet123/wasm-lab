//! html2png — read HTML on stdin, write a PNG on stdout.
//!
//! A WASI command, so the same binary runs under wasmtime, Node, or natively.
//! Everything here is vendored: Stylo parses the CSS, Taffy lays it out, Parley
//! shapes the text, vello_cpu rasterises. This file is only the plumbing.
use anyrender::ImageRenderer;
use anyrender_vello_cpu::VelloCpuImageRenderer;
use blitz_dom::{DocumentConfig, StyleThreading};
use blitz_html::HtmlDocument;
use blitz_traits::shell::{ColorScheme, Viewport};
use std::io::{Read, Write};

/// WASM has no system fonts, so they are embedded. Registering only a regular
/// face is a trap: `<th>`, `<b>` and `<i>` then have nothing to select, and the
/// resulting diff blames the engine for the harness's missing weights.
const FACES: [&[u8]; 3] = [
    include_bytes!("../font.ttf"),
    include_bytes!("../font-bold.ttf"),
    include_bytes!("../font-italic.ttf"),
];

fn build_font_ctx(faces: &[&[u8]]) -> blitz_dom::FontContext {
    use blitz_dom::decode_font_bytes;
    use parley::fontique::{Blob, Collection, CollectionOptions, GenericFamily, SourceCache};
    use std::sync::Arc;

    let mut ctx = blitz_dom::FontContext {
        source_cache: SourceCache::new_shared(),
        collection: Collection::new(CollectionOptions { shared: false, system_fonts: false }),
    };
    let mut families = Vec::new();
    for face in faces {
        let decoded = decode_font_bytes(face).into_owned();
        for (id, _) in ctx.collection.register_fonts(Blob::new(Arc::new(decoded) as _), None) {
            families.push(id);
        }
    }
    for generic in [GenericFamily::SansSerif, GenericFamily::Serif,
                    GenericFamily::Monospace, GenericFamily::SystemUi] {
        ctx.collection.append_generic_families(generic, families.iter().copied());
    }
    ctx
}

fn arg(n: usize, fallback: u32) -> u32 {
    std::env::args().nth(n).and_then(|a| a.parse().ok()).unwrap_or(fallback)
}

fn main() {
    let (width, height) = (arg(1, 800), arg(2, 600));

    let mut html = String::new();
    std::io::stdin().read_to_string(&mut html).expect("read stdin");

    let mut doc = HtmlDocument::from_html(
        &html,
        DocumentConfig {
            viewport: Some(Viewport::new(width, height, 1.0, ColorScheme::Light)),
            style_threading: StyleThreading::Sequential,
            font_ctx: Some(build_font_ctx(&FACES)),
            ..Default::default()
        },
    )
    .into_inner();
    doc.resolve(0.0);

    let mut renderer = VelloCpuImageRenderer::new(width, height);
    let mut pixels = Vec::new();
    renderer.render_to_vec(
        |scene| blitz_paint::paint_scene(scene, &mut doc, 1.0, width, height, 0, 0),
        &mut pixels,
    );

    let mut png_bytes = Vec::new();
    let mut encoder = png::Encoder::new(&mut png_bytes, width, height);
    encoder.set_color(png::ColorType::Rgba);
    encoder.set_depth(png::BitDepth::Eight);
    encoder.write_header().unwrap().write_image_data(&pixels).unwrap();

    std::io::stdout().write_all(&png_bytes).expect("write stdout");
}
