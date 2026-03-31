from pathlib import Path
import csv
import re
import unicodedata
from statistics import mean


def levenshtein(a, b):
    """
    Generic Levenshtein distance for strings or token lists.
    """
    if len(a) < len(b):
        a, b = b, a

    previous = list(range(len(b) + 1))

    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            ins = current[j - 1] + 1
            dele = previous[j] + 1
            sub = previous[j - 1] + (0 if ca == cb else 1)
            current.append(min(ins, dele, sub))
        previous = current

    return previous[-1]


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    return text.strip()


def normalize_hist_eval(text: str) -> str:
    """
    Light normalization for historical-text evaluation:
    - NFC/NFD normalization
    - ç -> z
    - remove accents except ñ
    - normalize internal whitespace
    - preserve line breaks
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)

    text = text.replace("ç", "z").replace("Ç", "Z")

    text = text.replace("ñ", "<<ENYE_LOWER>>")
    text = text.replace("Ñ", "<<ENYE_UPPER>>")

    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = unicodedata.normalize("NFC", text)

    text = text.replace("<<ENYE_LOWER>>", "ñ")
    text = text.replace("<<ENYE_UPPER>>", "Ñ")

    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)

    text = "\n".join(lines).strip()
    return text


def cer(ref: str, hyp: str):
    if len(ref) == 0:
        return 0.0 if len(hyp) == 0 else 1.0
    return levenshtein(ref, hyp) / len(ref)


def wer(ref: str, hyp: str):
    ref_tokens = ref.split()
    hyp_tokens = hyp.split()
    if len(ref_tokens) == 0:
        return 0.0 if len(hyp_tokens) == 0 else 1.0
    return levenshtein(ref_tokens, hyp_tokens) / len(ref_tokens)


def main():
    base_dir = Path(__file__).resolve().parent.parent
    eval_dir = base_dir / "outputs" / "gemini_eval"
    out_dir = base_dir / "outputs" / "metrics"
    out_dir.mkdir(parents=True, exist_ok=True)

    ocr_map = {}
    gemini_map = {}
    gt_map = {}

    for p in eval_dir.glob("*.ocr.txt"):
        stem = p.name[:-len(".ocr.txt")]
        ocr_map[stem] = p

    for p in eval_dir.glob("*.gemini.txt"):
        stem = p.name[:-len(".gemini.txt")]
        gemini_map[stem] = p

    for p in eval_dir.glob("*.gt.txt"):
        stem = p.name[:-len(".gt.txt")]
        gt_map[stem] = p

    stems = sorted(set(ocr_map) & set(gemini_map) & set(gt_map))

    if not stems:
        print("No complete OCR/Gemini/GT triplets found in outputs/gemini_eval.")
        return

    rows = []

    cer_ocr_raw_all = []
    cer_gem_raw_all = []
    wer_ocr_raw_all = []
    wer_gem_raw_all = []

    cer_ocr_norm_all = []
    cer_gem_norm_all = []
    wer_ocr_norm_all = []
    wer_gem_norm_all = []

    better_cer_raw = 0
    better_wer_raw = 0
    better_cer_norm = 0
    better_wer_norm = 0

    for stem in stems:
        ocr_text = read_text(ocr_map[stem])
        gem_text = read_text(gemini_map[stem])
        gt_text = read_text(gt_map[stem])

        ocr_norm = normalize_hist_eval(ocr_text)
        gem_norm = normalize_hist_eval(gem_text)
        gt_norm = normalize_hist_eval(gt_text)

        cer_ocr_raw = cer(gt_text, ocr_text)
        cer_gem_raw = cer(gt_text, gem_text)
        wer_ocr_raw = wer(gt_text, ocr_text)
        wer_gem_raw = wer(gt_text, gem_text)

        cer_ocr_norm = cer(gt_norm, ocr_norm)
        cer_gem_norm = cer(gt_norm, gem_norm)
        wer_ocr_norm = wer(gt_norm, ocr_norm)
        wer_gem_norm = wer(gt_norm, gem_norm)

        if cer_gem_raw < cer_ocr_raw:
            better_cer_raw += 1
        if wer_gem_raw < wer_ocr_raw:
            better_wer_raw += 1
        if cer_gem_norm < cer_ocr_norm:
            better_cer_norm += 1
        if wer_gem_norm < wer_ocr_norm:
            better_wer_norm += 1

        cer_ocr_raw_all.append(cer_ocr_raw)
        cer_gem_raw_all.append(cer_gem_raw)
        wer_ocr_raw_all.append(wer_ocr_raw)
        wer_gem_raw_all.append(wer_gem_raw)

        cer_ocr_norm_all.append(cer_ocr_norm)
        cer_gem_norm_all.append(cer_gem_norm)
        wer_ocr_norm_all.append(wer_ocr_norm)
        wer_gem_norm_all.append(wer_gem_norm)

        rows.append({
            "stem": stem,
            "gt_chars": len(gt_text),
            "gt_words": len(gt_text.split()),
            "cer_ocr_raw": cer_ocr_raw,
            "cer_gemini_raw": cer_gem_raw,
            "cer_gain_raw": cer_ocr_raw - cer_gem_raw,
            "wer_ocr_raw": wer_ocr_raw,
            "wer_gemini_raw": wer_gem_raw,
            "wer_gain_raw": wer_ocr_raw - wer_gem_raw,
            "cer_ocr_norm": cer_ocr_norm,
            "cer_gemini_norm": cer_gem_norm,
            "cer_gain_norm": cer_ocr_norm - cer_gem_norm,
            "wer_ocr_norm": wer_ocr_norm,
            "wer_gemini_norm": wer_gem_norm,
            "wer_gain_norm": wer_ocr_norm - wer_gem_norm,
        })

    csv_path = out_dir / "cer_wer_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "stem",
                "gt_chars",
                "gt_words",
                "cer_ocr_raw",
                "cer_gemini_raw",
                "cer_gain_raw",
                "wer_ocr_raw",
                "wer_gemini_raw",
                "wer_gain_raw",
                "cer_ocr_norm",
                "cer_gemini_norm",
                "cer_gain_norm",
                "wer_ocr_norm",
                "wer_gemini_norm",
                "wer_gain_norm",
            ]
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    summary_lines = []
    summary_lines.append(f"Number of evaluated pages: {len(stems)}")
    summary_lines.append("")
    summary_lines.append("=== RAW METRICS ===")
    summary_lines.append(f"Average CER OCR    : {mean(cer_ocr_raw_all):.6f}")
    summary_lines.append(f"Average CER Gemini : {mean(cer_gem_raw_all):.6f}")
    summary_lines.append(f"Average WER OCR    : {mean(wer_ocr_raw_all):.6f}")
    summary_lines.append(f"Average WER Gemini : {mean(wer_gem_raw_all):.6f}")
    summary_lines.append(f"Pages where Gemini improved CER (raw): {better_cer_raw}/{len(stems)}")
    summary_lines.append(f"Pages where Gemini improved WER (raw): {better_wer_raw}/{len(stems)}")
    summary_lines.append("")
    summary_lines.append("=== NORMALIZED METRICS ===")
    summary_lines.append(f"Average CER OCR    : {mean(cer_ocr_norm_all):.6f}")
    summary_lines.append(f"Average CER Gemini : {mean(cer_gem_norm_all):.6f}")
    summary_lines.append(f"Average WER OCR    : {mean(wer_ocr_norm_all):.6f}")
    summary_lines.append(f"Average WER Gemini : {mean(wer_gem_norm_all):.6f}")
    summary_lines.append(f"Pages where Gemini improved CER (norm): {better_cer_norm}/{len(stems)}")
    summary_lines.append(f"Pages where Gemini improved WER (norm): {better_wer_norm}/{len(stems)}")

    summary_path = out_dir / "summary.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print("Done.")
    print(f"Evaluated pages: {len(stems)}")
    print(f"Detailed CSV : {csv_path}")
    print(f"Summary TXT  : {summary_path}")


if __name__ == "__main__":
    main()