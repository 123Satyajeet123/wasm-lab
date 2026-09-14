"""Merge the chunked wasm reports and diff them against the native full-CSS run.

Only tests present in BOTH runs are compared. Chunking means an aborted chunk
contributes nothing, so coverage is reported honestly rather than silently
shrinking the denominator.
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).parent
NATIVE = HERE / "upstream/blitz/wpt/output-native-css/wptreport.json"
CHUNKS = HERE / "upstream/blitz/wpt/out-wasm-chunks"


def index(results):
    out = {}
    for t in results:
        out[t["test"]] = (t["status"], {s["name"]: s["status"] for s in t.get("subtests", [])})
    return out


def main():
    native = index(json.loads(NATIVE.read_text())["results"])

    wasm, chunks = {}, 0
    for report in sorted(CHUNKS.glob("*/wptreport.json")):
        wasm.update(index(json.loads(report.read_text())["results"]))
        chunks += 1

    both = set(native) & set(wasm)
    missing = set(native) - set(wasm)

    status_diff, sub_diff, subs = [], [], 0
    for name in both:
        sa, suba = native[name]
        sb, subb = wasm[name]
        if sa != sb:
            status_diff.append((name, sa, sb))
        subs += len(suba)
        for key in set(suba) | set(subb):
            if suba.get(key) != subb.get(key):
                sub_diff.append((name, key, suba.get(key), subb.get(key)))

    print(f"  chunk reports merged   {chunks}")
    print(f"  tests, native run      {len(native)}")
    print(f"  tests, wasm run        {len(wasm)}")
    print(f"  compared (in both)     {len(both)}   coverage {len(both)/len(native)*100:.1f}%")
    print(f"  subtests compared      {subs}")
    print(f"  missing from wasm      {len(missing)}")
    print()
    print(f"  TEST-LEVEL differences    {len(status_diff)}")
    print(f"  SUBTEST-LEVEL differences {len(sub_diff)}")
    for row in status_diff[:12]:
        print("     ", row)
    for row in sub_diff[:12]:
        print("     ", row)
    if missing and len(missing) < 2000:
        dirs = {}
        for m in missing:
            dirs[m.split("/")[1]] = dirs.get(m.split("/")[1], 0) + 1
        print("\n  missing by directory (top):")
        for d, n in sorted(dirs.items(), key=lambda kv: -kv[1])[:8]:
            print(f"     {d:<28} {n}")
    print()
    verdict = "IDENTICAL" if not status_diff and not sub_diff else "DIVERGENCE"
    print(f"  VERDICT: {verdict} across {len(both)} tests / {subs} subtests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
