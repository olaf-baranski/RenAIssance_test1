# Renaissance OCR + LLM Cleanup Pipeline

End-to-end pipeline for processing early modern printed texts:

PDF → OCR → LLM post-processing → evaluation

The goal is to test whether a multimodal LLM can improve OCR quality on historical documents.

---

## Overview

This project builds a reproducible pipeline for:

1. Extracting pages from historical PDFs
2. Generating ground truth from transcripts
3. Running OCR (Kraken)
4. Cleaning OCR output using a multimodal LLM (Gemini)
5. Evaluating improvements against ground truth

Focus: early modern Spanish printed texts with noisy typography and OCR challenges.

---

## Pipeline


PDF
-
PNG pages
-
(optional) split spreads
-
clean transcripts (GT)
-
Kraken segmentation → PAGE XML
-
line extraction (dataset)
-
Kraken OCR
-
Gemini cleanup (image + OCR)
-
Evaluation (CER/WER)


---

## Project Structure


data/
original_pdfs/
original_transcripts/
raw_pages/
train_pages_clean/
line_dataset/

outputs/
base_ocr/
gemini_json/
gemini_txt/
gemini_eval/
metrics/

src/
extract_pages.py
split_spreads.py
extract_transcripts.py
align_data.py
extract_line_dataset.py
evaluate_ocr_vs_gemini.py

run_base_ocr.sh
run_gemini_cleanup.sh


---

## Setup

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate

Install dependencies (example):

pip install kraken opencv-python pymupdf lxml pillow python-docx numpy
Usage
1. Extract pages from PDFs
python src/extract_pages.py
2. Split double-page scans
python src/split_spreads.py
3. Convert transcripts to clean text
python src/extract_transcripts.py
4. Align ground truth with pages
python src/align_data.py
5. Extract line-level dataset
python src/extract_line_dataset.py
6. Run baseline OCR
bash run_base_ocr.sh
7. Run Gemini cleanup
export GEMINI_API_KEY=your_key_here
bash run_gemini_cleanup.sh
8. Evaluate OCR vs Gemini
python src/evaluate_ocr_vs_gemini.py
Outputs
outputs/
  base_ocr/        # raw OCR text
  gemini_txt/      # cleaned text
  gemini_json/     # structured outputs
  gemini_eval/     # OCR vs Gemini vs GT triplets
  metrics/         # CER/WER results
Evaluation

The evaluation script computes:

Character Error Rate (CER)
Word Error Rate (WER)

Two modes are used:

Raw comparison (exact text)
Normalized comparison (historical normalization rules)

Normalization includes:

ç → z
accent removal (except ñ)
whitespace normalization
Experiment Goal

The central question is:

Can a multimodal LLM improve OCR output for early modern printed texts without introducing hallucinations?

The model is instructed to:

preserve historical spelling
avoid aggressive corrections
remove marginalia and noise
correct only high-confidence OCR errors
