#!/usr/bin/env bash
set -euo pipefail

# --- config ---
MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"
API_URL="https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent"
OCR_DIR="outputs/base_ocr"
RAW_DIR="data/raw_pages"
OUT_JSON_DIR="outputs/gemini_json"
OUT_TXT_DIR="outputs/gemini_txt"
OUT_EVAL_DIR="outputs/gemini_eval"
TMP_DIR=".tmp_gemini"

# Pages selected for evaluation (have OCR output + GT in raw_pages)
PAGES=(
  "BuendiaInstruccion_page_002_right"
  "BuendiaInstruccion_page_003_left"
  "BuendiaInstruccion_page_003_right"
  "BuendiaInstruccion_page_004_left"
  "BuendiaInstruccion_page_004_right"
  "CovarrubiasTesoro lengua_page_009"
  "GuardiolaTratado nobleza_page_013"
  "GuardiolaTratado nobleza_page_014"
  "PORCONES.23.51628_page_001"
  "PORCONES.23.51628_page_002_left"
  "PORCONES.23.51628_page_003_left"
  "PORCONES.23.51628_page_003_right"
  "PORCONES.23.51628_page_004_left"
  "PORCONES.228.381646_page_001"
  "PORCONES.228.381646_page_003"
  "PORCONES.228.381646_page_004"
  "PORCONES.228.381646_page_005"
  "PORCONES.748.61650_page_001"
  "PORCONES.748.61650_page_002"
  "PORCONES.748.61650_page_003"
)

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "ERROR: GEMINI_API_KEY is not set."
  echo "Run: export GEMINI_API_KEY='your_key_here'"
  exit 1
fi

mkdir -p "$OUT_JSON_DIR" "$OUT_TXT_DIR" "$OUT_EVAL_DIR" "$TMP_DIR"

# portable base64 flags
if [[ "$(base64 --version 2>&1 || true)" == *"FreeBSD"* ]]; then
  B64FLAGS="--input"
else
  B64FLAGS="-w0"
fi

for stem in "${PAGES[@]}"; do
  ocr_file="${OCR_DIR}/${stem}.txt"
  img_file="${RAW_DIR}/${stem}.png"
  gt_file="${RAW_DIR}/${stem}.txt"

  if [[ ! -f "$ocr_file" ]]; then
    echo "[SKIP] Missing OCR file: $ocr_file"
    continue
  fi
  if [[ ! -f "$img_file" ]]; then
    echo "[SKIP] Missing image: $img_file"
    continue
  fi
  if [[ ! -f "$gt_file" ]]; then
    echo "[SKIP] Missing GT file: $gt_file"
    continue
  fi

  echo "[RUN ] $stem"

  payload_file="${TMP_DIR}/payload.json"
  response_file="${TMP_DIR}/response.json"

  python3 - "$stem" "$ocr_file" "$img_file" > "$payload_file" <<'PY'
import base64
import json
import sys
from pathlib import Path

stem = sys.argv[1]
ocr_path = Path(sys.argv[2])
img_path = Path(sys.argv[3])

ocr_text = ocr_path.read_text(encoding="utf-8")
img_b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")

system_instruction = (
    "You are post-processing OCR output from early modern Spanish printed texts. "
    "Be extremely conservative. "
    "Keep only the main text of the page. "
    "Remove marginalia, catchwords/reklamants, obvious OCR garbage, and non-main-text noise. "
    "Preserve historical wording and spelling unless a correction is explicitly justified by the rules below. "
    "Keep line breaks in the cleaned_text output. "
    "Never invent missing content. If uncertain, prefer the OCR reading."
)

user_prompt = f"""
Page ID: {stem}

TASK:
Clean the OCR output for this single page using the page image as visual evidence.

GOALS:
1. Keep only the main text.
2. Remove marginalia, catchword/reklamant at the bottom, page furniture, and obvious non-text noise.
3. Correct only highly confident OCR mistakes.
4. Preserve line breaks in the cleaned_text field.

CONSERVATIVE RULES:
- Preserve historical spelling and wording unless a change is strongly justified.
- Always interpret ç as z.
- Ignore inconsistent accents, except preserve ñ as ñ.
- Treat u/v interchangeability cautiously and only when the OCR reading is clearly implausible.
- Treat long-s / f ambiguity cautiously and only when the OCR reading is clearly implausible.
- Some letters with a horizontal cap may imply n follows, or ue after capped q, but change only when highly confident.
- Do not aggressively rejoin line-end hyphenations. If uncertain, leave the split as it appears.
- Remove only obvious marginalia/reklamants/noise; do not delete real main text.

RETURN:
Return JSON only.

OCR TEXT:
<<<OCR_START
{ocr_text}
OCR_END>>>
""".strip()

payload = {
    "system_instruction": {
        "parts": [
            {"text": system_instruction}
        ]
    },
    "contents": [
        {
            "role": "user",
            "parts": [
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": img_b64
                    }
                },
                {
                    "text": user_prompt
                }
            ]
        }
    ],
    "generationConfig": {
        "temperature": 0.1,
        "responseMimeType": "application/json",
        "responseJsonSchema": {
            "type": "object",
            "properties": {
                "cleaned_text": {
                    "type": "string",
                    "description": "Main text only, cleaned conservatively, preserving line breaks with \\n."
                },
                "removed_noise": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Short list of removed marginalia, catchwords, or obvious OCR garbage."
                },
                "uncertain_cases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of uncertain readings left unresolved or changed cautiously."
                }
            },
            "required": ["cleaned_text", "removed_noise", "uncertain_cases"]
        }
    }
}

print(json.dumps(payload, ensure_ascii=False))
PY

  curl -sS "${API_URL}?key=${GEMINI_API_KEY}" \
    -H 'Content-Type: application/json' \
    -X POST \
    -d @"$payload_file" \
    > "$response_file"

  python3 - "$stem" "$response_file" "$OUT_JSON_DIR" "$OUT_TXT_DIR" "$OUT_EVAL_DIR" "$ocr_file" "$gt_file" <<'PY'
import json
import sys
from pathlib import Path

stem = sys.argv[1]
response_path = Path(sys.argv[2])
out_json_dir = Path(sys.argv[3])
out_txt_dir = Path(sys.argv[4])
out_eval_dir = Path(sys.argv[5])
ocr_file = Path(sys.argv[6])
gt_file = Path(sys.argv[7])

raw = json.loads(response_path.read_text(encoding="utf-8"))

# Save raw API response for debugging
(out_json_dir / f"{stem}.raw_api.json").write_text(
    json.dumps(raw, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

try:
    text = raw["candidates"][0]["content"]["parts"][0]["text"]
except Exception as e:
    raise SystemExit(f"[ERROR] Could not extract model text for {stem}: {e}")

obj = json.loads(text)

(out_json_dir / f"{stem}.json").write_text(
    json.dumps(obj, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

cleaned = obj["cleaned_text"]
(out_txt_dir / f"{stem}.txt").write_text(cleaned, encoding="utf-8")

# Convenience copies for evaluation later
(out_eval_dir / f"{stem}.ocr.txt").write_text(
    ocr_file.read_text(encoding="utf-8"),
    encoding="utf-8"
)
(out_eval_dir / f"{stem}.gemini.txt").write_text(
    cleaned,
    encoding="utf-8"
)
(out_eval_dir / f"{stem}.gt.txt").write_text(
    gt_file.read_text(encoding="utf-8"),
    encoding="utf-8"
)
PY

  echo "[OK  ] $stem"
done

echo "Done."
echo "Cleaned JSON: $OUT_JSON_DIR"
echo "Cleaned TXT : $OUT_TXT_DIR"
echo "Eval triples: $OUT_EVAL_DIR"