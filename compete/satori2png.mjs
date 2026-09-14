// Same contract as html2png.wasm: HTML on stdin, PNG on stdout, [width height].
// Lets the conformance harness score Satori on identical pages with an
// identical metric, instead of trusting either project's own claims.
import { readFileSync } from "node:fs";
import satori from "satori";
import { html } from "satori-html";
import { Resvg } from "@resvg/resvg-js";
import { join } from "node:path";

const [width, height] = [Number(process.argv[2]) || 900, Number(process.argv[3]) || 600];
const source = readFileSync(0, "utf8");

const fonts = [
  { name: "Arial", data: readFileSync(join(import.meta.dirname, "../html2png/font.ttf")), weight: 400, style: "normal" },
  { name: "Arial", data: readFileSync(join(import.meta.dirname, "../html2png/font-bold.ttf")), weight: 700, style: "normal" },
  { name: "Arial", data: readFileSync(join(import.meta.dirname, "../html2png/font-italic.ttf")), weight: 400, style: "italic" },
];

try {
  const svg = await satori(html(source), { width, height, fonts });
  const png = new Resvg(svg, { fitTo: { mode: "width", value: width } }).render().asPng();
  process.stdout.write(png);
} catch (err) {
  process.stderr.write(String(err?.message ?? err) + "\n");
  process.exit(1);
}
