#!/usr/bin/env bash
# Clone the upstream trees the WPT comparison needs. Not committed: Blitz plus
# its target dir is ~2 GB, and WPT at the pinned revision is 1.1 GB / 163k files.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p upstream && cd upstream

WPT_COMMIT=5a5b2b591b39c59d5bca77819db305474dcfd18a   # matches Blitz CI
BLITZ_COMMIT=450e576dd4b1fe8cd1def09facf9c73c6c1006ed

[ -d wpt-tests ] || git clone --depth 1 --revision "$WPT_COMMIT" \
  https://github.com/web-platform-tests/wpt wpt-tests
[ -d blitz ] || git clone --depth 1 --revision "$BLITZ_COMMIT" \
  https://github.com/DioxusLabs/blitz blitz

ln -sfn ../../wpt-tests blitz/wpt/tests
echo "done. see TESTING.md section 5."
