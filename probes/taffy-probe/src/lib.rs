use taffy::prelude::*;

#[unsafe(no_mangle)]
pub extern "C" fn layout_probe(width: f32, height: f32) -> f32 {
    let mut tree: TaffyTree<()> = TaffyTree::new();
    let kids: Vec<_> = (0..24)
        .map(|i| tree.new_leaf(Style { size: Size { width: length(20.0 + i as f32), height: length(16.0) }, ..Default::default() }).unwrap())
        .collect();
    let root = tree.new_with_children(
        Style { display: Display::Flex, flex_wrap: FlexWrap::Wrap,
                size: Size { width: length(width), height: length(height) }, ..Default::default() },
        &kids).unwrap();
    tree.compute_layout(root, Size::MAX_CONTENT).unwrap();
    tree.layout(kids[23]).unwrap().location.y
}
