#!/usr/bin/env bash
# Prints the built CV page to a PDF and puts it at <site>/files/schwartz-cv.pdf,
# so the "Download PDF" button always matches the data on the site.
#
# Usage: _tools/make_cv_pdf.sh [site-dir]     (default: _site)
#
# Run it after Jekyll has built the site. It serves the built site on
# localhost, has headless Chrome print /cv/ with the page's own print
# stylesheet (every list fully open, no screen-only buttons), and checks the
# result. If anything goes wrong it leaves the PDF that is already in the
# site (the copy committed in files/) alone and exits 0, so a PDF problem can
# never stop a publish. The workflow log says which case happened.
set -u

SITE="${1:-_site}"
PORT=8765
OUT="$SITE/files/schwartz-cv.pdf"
MIN_BYTES="${CV_PDF_MIN_BYTES:-100000}"   # a real CV is several hundred KB
MIN_PAGES="${CV_PDF_MIN_PAGES:-10}"       # the printed CV is about 30 pages

keep_old() { echo "CV PDF: $1; keeping the existing $OUT"; exit 0; }

[ -f "$SITE/cv/index.html" ] || keep_old "no $SITE/cv/index.html"

CHROME="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"
[ -n "$CHROME" ] || keep_old "no Chrome on this machine"

TMP="$(mktemp -d)"
( cd "$SITE" && exec python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 ) &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null; rm -rf "$TMP"' EXIT
sleep 2

"$CHROME" --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=20000 --print-to-pdf="$TMP/cv.pdf" \
  "http://127.0.0.1:$PORT/cv/" >"$TMP/chrome.log" 2>&1 || {
  tail -5 "$TMP/chrome.log"; keep_old "Chrome failed"; }

[ -s "$TMP/cv.pdf" ] || keep_old "Chrome wrote no file"
BYTES="$(stat -c %s "$TMP/cv.pdf")"
if command -v pdfinfo >/dev/null 2>&1; then
  PAGES="$(pdfinfo "$TMP/cv.pdf" 2>/dev/null | awk '/^Pages:/ {print $2}')"
else
  PAGES="$(python3 -c "import re,sys; print(len(re.findall(rb'/Type\\s*/Page\\b', open(sys.argv[1],'rb').read())))" "$TMP/cv.pdf")"
fi
PAGES="${PAGES:-0}"
[ "$BYTES" -ge "$MIN_BYTES" ] || keep_old "new PDF is only $BYTES bytes"
[ "$PAGES" -ge "$MIN_PAGES" ] || keep_old "new PDF has only $PAGES pages"

mkdir -p "$SITE/files"
cp "$TMP/cv.pdf" "$OUT"
echo "CV PDF: wrote $OUT ($PAGES pages, $BYTES bytes)"
