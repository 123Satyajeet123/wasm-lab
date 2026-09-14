#!/usr/bin/env bash
# Fetch openly-licensed font faces so the renderer can be built.
#
# The conformance numbers in RESULTS.md were measured with the macOS system
# Arial, which cannot be redistributed, so it is not in this repo. DejaVu Sans
# is metrically different, so re-running compare.py with these faces will shift
# the text-heavy rows slightly. The wasm-vs-native comparison is unaffected:
# both targets use whatever faces are here.
set -euo pipefail
cd "$(dirname "$0")/html2png"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

echo "fetching DejaVu Sans (Bitstream Vera / Public Domain)"
curl -sSfL -o "$TMP/dejavu.zip" \
  https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip
unzip -q -o "$TMP/dejavu.zip" -d "$TMP"
SRC="$TMP/dejavu-fonts-ttf-2.37/ttf"
cp "$SRC/DejaVuSans.ttf"            font.ttf
cp "$SRC/DejaVuSans-Bold.ttf"       font-bold.ttf
cp "$SRC/DejaVuSans-Oblique.ttf"    font-italic.ttf

mkdir -p subset
if command -v pyftsubset >/dev/null 2>&1; then
  RANGES="U+0000-00FF,U+2000-206F,U+2070-209F,U+20A0-20BF,U+2190-21FF,U+2200-22FF,U+25A0-25FF,U+2600-26FF"
  for f in font font-bold font-italic; do
    pyftsubset "$f.ttf" --output-file="subset/$f.ttf" --unicodes="$RANGES" --layout-features='*'
  done
  echo "subset to Latin + symbols (pyftsubset)"
else
  cp font.ttf font-bold.ttf font-italic.ttf subset/
  echo "pyftsubset not found (pip install fonttools) — using full faces, ~2 MB larger"
fi
echo "done. now: cd html2png && cargo build --release --target wasm32-wasip1"
