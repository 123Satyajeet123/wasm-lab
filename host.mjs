// In-process cold start: compile once, then instantiate+call repeatedly.
// This is the number an edge runtime actually pays, without process spawn.
// Usage: node host.mjs <module.wasm> <export> [args...]
import { readFileSync } from "node:fs";
import { WASI } from "node:wasi";

const [file, fn, ...rest] = process.argv.slice(2);
const args = rest.map(Number);
const bytes = readFileSync(file);
const now = () => Number(process.hrtime.bigint()) / 1e6;
const median = a => a.slice().sort((x, y) => x - y)[a.length >> 1];

let t0 = now();
const mod = await WebAssembly.compile(bytes);
const compileMs = now() - t0;

const needsWasi = WebAssembly.Module.imports(mod).some(i => i.module.startsWith("wasi_"));
const inst = [], call = [];
let result;
for (let i = 0; i < 20; i++) {
  // A wasip1 cdylib is a reactor, not a command: its exports are only callable
  // after initialize() runs the module's constructors.
  const wasi = needsWasi ? new WASI({ version: "preview1", args: [], env: {} }) : null;
  t0 = now();
  const instance = await WebAssembly.instantiate(mod, wasi ? wasi.getImportObject() : {});
  if (wasi) (instance.exports._start ? wasi.start : wasi.initialize).call(wasi, instance);
  inst.push(now() - t0);
  t0 = now();
  result = instance.exports[fn](...args);
  call.push(now() - t0);
}
console.log(`  compile       ${compileMs.toFixed(1).padStart(8)} ms  (cacheable)`);
console.log(`  instantiate   ${median(inst).toFixed(2).padStart(8)} ms  (median of 20)`);
console.log(`  ${fn.padEnd(13)}${median(call).toFixed(2).padStart(8)} ms  -> ${result}`);
