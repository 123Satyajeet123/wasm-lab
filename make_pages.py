"""Feature-partitioned conformance pages.

Arial is pinned everywhere so the diff measures layout and paint, not font
choice — the embedded WASM font and Chrome's Arial are then the same face.
"""
import pathlib

HEAD = ("<!doctype html><meta charset=utf-8><style>"
        "*{box-sizing:border-box}html,body{margin:0;padding:0}"
        "body{font:16px/1.5 Arial,sans-serif;color:#16202a;background:#fff;padding:20px}")

PAGES = {
"block": ".a{background:#dce7ea;padding:20px;margin:0 0 16px}.b{background:#0e6e6e;color:#fff;padding:14px;margin:10px 24px}.c{background:#f0c98a;padding:8px;margin:6px}"
         "</style><div class=a><div class=b>nested b<div class=c>c</div></div></div><div class=a>sibling</div>",

"flex": ".r{display:flex;gap:12px;margin-bottom:14px}.r>div{background:#dce7ea;padding:12px}"
        ".g1>div:nth-child(2){flex:1}.ctr{justify-content:center}.btw{justify-content:space-between}"
        ".col{flex-direction:column;height:120px;justify-content:space-around}.wrap{flex-wrap:wrap;width:300px}"
        "</style><div class='r g1'><div>a</div><div>grow</div><div>c</div></div>"
        "<div class='r ctr'><div>centered</div><div>pair</div></div>"
        "<div class='r btw'><div>left</div><div>right</div></div>"
        "<div class='r col'><div>col a</div><div>col b</div></div>"
        "<div class='r wrap'><div>w1</div><div>w2</div><div>w3</div><div>w4</div></div>",

"grid": ".g{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}"
        ".g>div{background:#dce7ea;padding:14px}.s2{grid-column:span 2}.s3{grid-column:span 3}"
        ".r2{display:grid;grid-template-columns:120px 1fr 80px;grid-template-rows:60px 40px;gap:8px}"
        ".r2>div{background:#f0c98a;padding:6px}"
        "</style><div class=g><div>1</div><div class=s2>span2</div><div>4</div><div class=s3>span3</div><div>x</div></div>"
        "<div class=r2><div>a</div><div>b</div><div>c</div><div>d</div><div>e</div><div>f</div></div>",

"text": "p{max-width:420px;margin:0 0 14px}.ls{letter-spacing:3px}.rt{text-align:right}.jt{text-align:justify}"
        ".up{text-transform:uppercase}.th{line-height:2.4}"
        "</style><p>The quick brown fox jumps over the lazy dog and keeps running until the line must break somewhere sensible.</p>"
        "<p class=ls>letter spaced text wrapping across lines</p><p class=rt>right aligned paragraph text here</p>"
        "<p class=jt>Justified text needs enough words to stretch across the full measure of the column.</p>"
        "<p class=up>uppercase transform</p><p class=th>tall line height paragraph that wraps onto two lines</p>",

"borders": "div{margin:0 0 12px;padding:10px;width:300px}.s{border:4px solid #0e6e6e}.d{border:4px dashed #a33a2e}"
           ".t{border:3px dotted #16202a}.r{border:4px solid #0e6e6e;border-radius:18px}"
           ".m{border-top:6px solid #0e6e6e;border-right:2px dashed #a33a2e;border-bottom:6px double #16202a;border-left:10px solid #f0c98a}"
           ".c{border:3px solid #16202a;border-radius:30px 4px 30px 4px}"
           "</style><div class=s>solid</div><div class=d>dashed</div><div class=t>dotted</div><div class=r>radius</div><div class=m>mixed</div><div class=c>corners</div>",

"table": "table{border-collapse:collapse;margin-bottom:16px}td,th{border:1px solid #16202a;padding:8px 14px}"
         "th{background:#dce7ea}tfoot td{background:#f0c98a}.sep{border-collapse:separate;border-spacing:6px}"
         "</style><table><thead><tr><th>col a</th><th>col b</th><th>col c</th></tr></thead>"
         "<tbody><tr><td colspan=2>colspan two</td><td>z</td></tr><tr><td>1</td><td>2</td><td>3</td></tr></tbody>"
         "<tfoot><tr><td>f1</td><td>f2</td><td>f3</td></tr></tfoot></table>"
         "<table class=sep><tr><td>sep</td><td>arated</td></tr><tr><td>border</td><td>spacing</td></tr></table>",

"position": ".rel{position:relative;height:200px;background:#dce7ea;margin-bottom:16px}"
            ".abs{position:absolute;background:#0e6e6e;color:#fff;padding:8px}"
            ".tl{top:10px;left:10px}.br{bottom:10px;right:10px}.ctr{top:50%;left:50%}"
            ".off{position:relative;top:14px;left:30px;background:#f0c98a;padding:8px;width:160px}"
            "</style><div class=rel><div class='abs tl'>top left</div><div class='abs br'>bottom right</div><div class='abs ctr'>50/50</div></div>"
            "<div class=off>relative offset</div>",

"inline": ".ib{display:inline-block;background:#dce7ea;padding:8px;margin:4px}"
          ".vt{vertical-align:top}.vb{vertical-align:bottom}.tall{height:70px}"
          ".nw{white-space:nowrap;overflow:hidden;width:260px;background:#f0c98a}"
          "</style><div><span class='ib tall'>tall</span><span class='ib vt'>top</span><span class='ib vb'>bottom</span><span class=ib>base</span></div>"
          "<p>inline <b>bold</b> and <i>italic</i> and <code>mono</code> mixed in a sentence that wraps at some point here.</p>"
          "<div class=nw>no wrap clipped line of text that overflows its box</div>",

"overflow": ".box{width:240px;height:110px;background:#dce7ea;margin-bottom:14px;padding:8px}"
            ".hid{overflow:hidden}.scr{overflow:scroll}.clip{overflow:hidden;border-radius:20px;background:#0e6e6e;color:#fff}"
            "</style><div class='box hid'>hidden overflow with a lot of repeated text that will certainly not fit inside this small box at all</div>"
            "<div class='box clip'>radius clipping content that spills past the rounded corner region of this element</div>",

"zindex": ".s{position:relative;height:180px}.l{position:absolute;width:120px;height:120px;padding:6px;color:#fff}"
          ".one{background:#0e6e6e;left:20px;top:20px;z-index:1}.two{background:#a33a2e;left:70px;top:50px;z-index:3}"
          ".three{background:#16202a;left:120px;top:10px;z-index:2}"
          "</style><div class=s><div class='l one'>z1</div><div class='l two'>z3</div><div class='l three'>z2</div></div>",

"gradient": "div{height:70px;margin-bottom:12px;padding:8px;color:#fff}"
            ".a{background:linear-gradient(90deg,#0e6e6e,#f0c98a)}"
            ".b{background:linear-gradient(180deg,#16202a,#dce7ea)}"
            ".c{background:linear-gradient(45deg,#a33a2e 0%,#f0c98a 50%,#0e6e6e 100%)}"
            ".d{background:#dce7ea;border-radius:14px;color:#16202a}"
            "</style><div class=a>horizontal</div><div class=b>vertical</div><div class=c>diagonal stops</div><div class=d>flat</div>",

"transform": ".s{height:230px;position:relative}.t{position:absolute;width:110px;height:60px;background:#0e6e6e;color:#fff;padding:6px}"
             ".r{left:20px;top:20px;transform:rotate(15deg)}.sc{left:190px;top:20px;transform:scale(1.3)}"
             ".tr{left:360px;top:20px;transform:translate(20px,30px)}.sk{left:20px;top:130px;transform:skewX(-12deg);background:#a33a2e}"
             "</style><div class=s><div class='t r'>rotate</div><div class='t sc'>scale</div><div class='t tr'>translate</div><div class='t sk'>skew</div></div>",

"list": "ul,ol{margin:0 0 14px}li{margin:3px 0}.sq{list-style:square}.rm{list-style:upper-roman}.none{list-style:none;padding-left:0}"
        "</style><ul><li>bullet one</li><li>bullet two<ul><li>nested a</li><li>nested b</li></ul></li></ul>"
        "<ol><li>first</li><li>second</li><li>third</li></ol>"
        "<ul class=sq><li>square</li><li>square two</li></ul>"
        "<ol class=rm><li>roman</li><li>roman two</li></ol><ul class=none><li>no marker</li></ul>",

"typography": "h1,h2,h3,h4{margin:0 0 8px}h1{font-size:34px}h2{font-size:26px}h3{font-size:20px}h4{font-size:16px}"
              ".sm{font-size:12px;color:#5d6b78}.bold{font-weight:700}.thin{font-weight:300}"
              "</style><h1>Heading one</h1><h2>Heading two</h2><h3>Heading three</h3><h4>Heading four</h4>"
              "<p class=bold>Bold body text</p><p class=thin>Light body text</p><p class=sm>Small muted caption text</p>"
              "<p><b>bold</b> <i>italic</i> <u>underline</u> <s>strike</s> <sub>sub</sub> <sup>sup</sup></p>",
}

out = pathlib.Path("pages")
out.mkdir(exist_ok=True)
for name, body in PAGES.items():
    (out / f"{name}.html").write_text(HEAD + body)
print(f"{len(PAGES)} pages written")
