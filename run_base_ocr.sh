#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="data/raw_pages"
OUTPUT_DIR="outputs/base_ocr"
MODEL="/home/olaf/.local/share/htrmopo/d96caf7a-122e-5576-ab2b-a246c4e64221/catmus-print-fondue-large.mlmodel"

mkdir -p "$OUTPUT_DIR"

count=0

find "$INPUT_DIR" -maxdepth 1 -type f -name "*.png" -print0 | while IFS= read -r -d '' f; do
    stem="$(basename "${f%.png}")"
    echo "Processing: $stem"

    kraken -i "$f" "$OUTPUT_DIR/${stem}.txt" segment -bl ocr -m "$MODEL"

    count=$((count + 1))
done

echo "Done."
echo "OCR outputs saved in: $OUTPUT_DIR"