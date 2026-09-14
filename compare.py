"""Score any HTML->PNG renderer against Chrome on the same pages.

Not the conformance suite — that is WPT, run via upstream/blitz/wpt. This exists
to compare *different renderers* (Blitz vs Satori) on one metric, which WPT
cannot do because Satori cannot run WPT.

A page passes when >=99% of its pixels are within a small per-channel delta of
Chrome's. Antialiasing will never match exactly; that tolerance is the point.
Failures are reported per feature so the number says what to fix, not just that
something is wrong.
"""
import os, pathlib, signal, subprocess, sys, tempfile, time
import cv2, numpy as np

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Any renderer that takes HTML on stdin and emits PNG on stdout. Defaults to
# the wasm build; set RENDERER to compare a different engine or revision.
RENDERER = os.environ.get(
    "RENDERER",
    "wasmtime run html2png/target/wasm32-wasip1/release/html2png.wasm").split()
W, H = 900, 600
TOLERANCE = 12          # per-channel; antialiasing noise lives below this
PASS_FRACTION = 0.99
BLUR = 3                # a different rasteriser disagrees on glyph edges even
                        # when every box is in the identical place. Blurring by
                        # a few pixels erases that disagreement and keeps real
                        # positional error, which is the thing worth measuring.

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"


def chrome_shot(page: pathlib.Path, dest: pathlib.Path) -> bool:
    """Chrome writes the screenshot and then does not exit, so wait for the
    file to stop growing and kill the process group rather than join it."""
    dest.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.Popen(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--force-device-scale-factor=1", f"--window-size={W},{H}",
             f"--user-data-dir={profile}", "--default-background-color=FFFFFFFF",
             "--disable-component-update", "--no-first-run",
             f"--screenshot={dest}", page.resolve().as_uri()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        deadline, last = time.time() + 45, -1
        while time.time() < deadline:
            size = dest.stat().st_size if dest.exists() else 0
            if size > 0 and size == last:
                break
            last = size
            if proc.poll() is not None and size > 0:
                break
            time.sleep(0.3)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10)
    return dest.exists() and dest.stat().st_size > 0


def wasm_render(page: pathlib.Path, dest: pathlib.Path) -> bool:
    with open(page) as fin, open(dest, "wb") as fout:
        r = subprocess.run(RENDERER + [str(W), str(H)],
                           stdin=fin, stdout=fout, stderr=subprocess.PIPE, timeout=120)
    return r.returncode == 0 and dest.stat().st_size > 0


def compare(a_path, b_path):
    a = cv2.imread(str(a_path), cv2.IMREAD_COLOR)
    b = cv2.imread(str(b_path), cv2.IMREAD_COLOR)
    if a is None or b is None:
        return None
    h = min(a.shape[0], b.shape[0])
    a, b = a[:h], b[:h]
    delta = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    ka = (BLUR * 2 + 1, BLUR * 2 + 1)
    blurred = np.abs(cv2.GaussianBlur(a, ka, 0).astype(np.int16)
                     - cv2.GaussianBlur(b, ka, 0).astype(np.int16)).max(axis=2)
    return {
        "exact": float((delta == 0).mean()),
        "within": float((delta <= TOLERANCE).mean()),
        "layout": float((blurred <= TOLERANCE).mean()),
        "shift": best_shift(a, b),
        "diff": (blurred > TOLERANCE).astype(np.uint8) * 255,
    }


def best_shift(a, b, radius=6):
    """If two renders differ only by a translation, say so — a uniform offset is
    a different bug from a scattered one, and the number names which."""
    ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float32)
    best, where = None, (0, 0)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            shifted = np.roll(np.roll(gb, dy, axis=0), dx, axis=1)
            score = np.abs(ga - shifted)[radius:-radius, radius:-radius].mean()
            if best is None or score < best:
                best, where = score, (dx, dy)
    return where


def main():
    OUT.mkdir(exist_ok=True)
    pages = sorted((HERE / "pages").glob("*.html"))
    rows, passed = [], 0
    for page in pages:
        name = page.stem
        c, w = OUT / f"{name}_chrome.png", OUT / f"{name}_wasm.png"
        if not chrome_shot(page, c):
            rows.append((name, None, "chrome failed")); continue
        if not wasm_render(page, w):
            rows.append((name, None, "render failed")); continue
        m = compare(c, w)
        if m is None:
            rows.append((name, None, "unreadable")); continue
        ok = m["layout"] >= PASS_FRACTION
        passed += ok
        cv2.imwrite(str(OUT / f"{name}_diff.png"), m["diff"])
        rows.append((name, m, "PASS" if ok else "FAIL"))

    print(f"{'feature':<12} {'exact':>8} {'within':>8} {'layout':>8} {'shift':>9}   verdict")
    print("-" * 60)
    for name, m, verdict in rows:
        if m is None:
            print(f"{name:<12} {'-':>8} {'-':>8} {'-':>8} {'-':>9}   {verdict}")
        else:
            print(f"{name:<12} {m['exact']*100:7.2f}% {m['within']*100:7.2f}% "
                  f"{m['layout']*100:7.2f}% {str(m['shift']):>9}   {verdict}")
    print("-" * 60)
    print(f"pass rate: {passed}/{len(pages)} = {passed/len(pages)*100:.0f}%"
          f"   (pass = >={PASS_FRACTION*100:.0f}% of pixels within {TOLERANCE} after {BLUR}px blur)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
