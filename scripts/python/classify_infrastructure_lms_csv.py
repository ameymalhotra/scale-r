"""
classify_infrastructure_lms_csv.py
───────────────────────────────────────────────────────────────────────────────
Classifies infrastructure type for the new LMS projects in the Claude-merged
dataset CSV that have an empty `Infrastruc` value, using a local Ollama model
(qwen2.5:7b), the shared type definitions, and existing classified projects as
few-shot examples. Uses title (Project_Na) and long description (OLD___Brie).
Few-shot examples are drawn from professor-reviewed LMS projects in
data/reviewed/professor_review_infrastructure_2026-06-09.xlsx.

This is the CSV sibling of classify_infrastructure_ollama.py (which targets the
older merged Excel). Two key differences:
  - Reads/writes the Claude-merged CSV in data/Merged Using Claude/.
  - Emits SHORT labels (Blue | Green | Gray | Hybrid) to match the values already
    used in that file, not the long "… Infrastructure" form.

Modes:
  --test (default): classify a sample of empty-Infrastruc rows, write a review
    CSV only. Does NOT modify the dataset.
  --full: classify ALL empty-Infrastruc rows and write a new, classified CSV
    (the original Claude-merged file is left untouched) plus an audit log.

Requires: Ollama running with the model pulled (ollama pull qwen2.5:7b).

USAGE
─────
  pip install -r scripts/python/requirements.txt
  python3 scripts/python/classify_infrastructure_lms_csv.py            # test sample
  python3 scripts/python/classify_infrastructure_lms_csv.py --full     # write classified CSV
  python3 scripts/python/classify_infrastructure_lms_csv.py --no-delay # skip pause between calls

METHODOLOGY
───────────
  See docs/LMS_DATA_PIPELINE.md
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
import infra_common as infra

# ── CONFIG ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_CSV = ROOT / "data" / "Merged Using Claude" / "OurDataset_updated_DESC_summarized.csv"
OUTPUT_CSV = ROOT / "data" / "Merged Using Claude" / "OurDataset_updated_DESC_INFRA_classified.csv"
DEFINITIONS_JSON = ROOT / "data" / "input" / "infrastructure_type_definitions.json"
LOG_OUTPUT_DIR = ROOT / "data" / "output" / "logs"

TITLE_COL = "Project_Na"
DESC_COL = "OLD___Brie"
INFRA_COL = "Infrastruc"

TEST_SAMPLE_SIZE = 30
RANDOM_SEED = 42
OLLAMA_MODEL = "qwen2.5:7b"
DELAY_SECONDS = 1.0
N_EXAMPLES_PER_LABEL = 6

# Short labels, matching the values already present in the dataset.
ALLOWED_LABELS = infra.ALLOWED_LABELS
DEFINITION_KEY_TO_LABEL = infra.DEFINITION_KEY_TO_LABEL
# ─────────────────────────────────────────────────────────────────────────────


def safe_str(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def load_definitions(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Definitions file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_empty_infra(val) -> bool:
    return safe_str(val) == ""


def parse_label(raw: str) -> str:
    """Normalize a model/string value to one of ALLOWED_LABELS. Default: Gray."""
    if not raw or not isinstance(raw, str):
        return "Gray"
    lower = raw.strip().lower()

    # Exact short-label match
    for label in ALLOWED_LABELS:
        if label.lower() == lower:
            return label
    # Keyword containment (handles "Gray Infrastructure", "grayish", etc.)
    if "hybrid" in lower:
        return "Hybrid"
    if "blue" in lower:
        return "Blue"
    if "green" in lower:
        return "Green"
    if "gray" in lower or "grey" in lower:
        return "Gray"
    return "Gray"


def parse_response(raw: str) -> tuple[str, str, str]:
    """Parse model JSON into (label, confidence, reasoning) with graceful fallback."""
    if not raw:
        return "Gray", "low", ""
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        data = json.loads(clean)
        label = parse_label(data.get("type", ""))
        confidence = str(data.get("confidence", "low")).strip().lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "low"
        reasoning = str(data.get("reasoning", "")).strip()
        return label, confidence, reasoning
    except (json.JSONDecodeError, AttributeError, IndexError):
        return parse_label(raw), "low", ""


def call_ollama(prompt: str) -> str:
    try:
        from ollama import chat
    except ImportError:
        raise ImportError("Install the ollama package: pip install ollama")
    response = chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0},
    )
    content = (
        getattr(response, "message", None)
        and getattr(response.message, "content", None)
    )
    return (content or "").strip()


def run_classification(df, definitions, row_indices, delay_sec=DELAY_SECONDS) -> list[dict]:
    if not infra.PROFESSOR_REVIEW_XLSX.exists():
        raise FileNotFoundError(f"Professor review file not found: {infra.PROFESSOR_REVIEW_XLSX}")

    print("\nBuilding few-shot examples from professor-reviewed LMS projects...")
    infra.load_professor_review_fewshot(n_per_label=N_EXAMPLES_PER_LABEL, seed=RANDOM_SEED)
    print()

    results = []
    total = len(row_indices)
    for i, df_idx in enumerate(row_indices):
        row = df.loc[df_idx]
        title = safe_str(row.get(TITLE_COL))
        description = safe_str(row.get(DESC_COL))
        examples = infra.load_professor_review_fewshot(
            n_per_label=N_EXAMPLES_PER_LABEL,
            seed=RANDOM_SEED,
            exclude_indices={df_idx},
            quiet=True,
        )

        prompt = infra.build_prompt(
            definitions, examples, title, description, label_map=DEFINITION_KEY_TO_LABEL
        )
        raw = call_ollama(prompt)
        label, confidence, reasoning = parse_response(raw)

        results.append({
            "df_index": df_idx,
            "Project_Na": title,
            "description": description,
            "description_snippet": (description[:400] + "...") if len(description) > 400 else description,
            "Infrastruc_predicted": label,
            "confidence": confidence,
            "reasoning": reasoning,
            "raw_response": raw,
        })
        print(f"  [{i+1}/{total}] {title[:55]:<55} -> {label:<7} ({confidence})")
        if delay_sec > 0 and i < total - 1:
            time.sleep(delay_sec)
    return results


def print_summary(results: list[dict]) -> None:
    label_counts = Counter(r["Infrastruc_predicted"] for r in results)
    confidence_counts = Counter(r["confidence"] for r in results)
    print("\n─── CLASSIFICATION SUMMARY ─────────────────────────────────────────────────────")
    print("By type:")
    for label in ALLOWED_LABELS:
        print(f"  {label:<10} {label_counts.get(label, 0)}")
    print("By confidence:")
    for level in ("high", "medium", "low"):
        print(f"  {level:<10} {confidence_counts.get(level, 0)}")
    low = confidence_counts.get("low", 0)
    if low:
        print(f"\n  {low} low-confidence result(s) should be prioritized for manual review.")
    print("────────────────────────────────────────────────────────────────────────────────\n")


def write_log(results: list[dict], mode: str) -> Path:
    LOG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"classify_infrastructure_lms_csv_{mode}_{date.today().isoformat()}.csv"
    path = LOG_OUTPUT_DIR / name
    # Test review CSV gets the full description for easier manual review;
    # production keeps the compact snippet.
    # Always log the full description (not a snippet) so reviewers have the complete
    # text when correcting labels. `manual_correction` is left blank for a human to fill
    # in the corrected label; `correction_notes` is free-form review notes.
    pd.DataFrame([
        {
            "df_index": r["df_index"],
            "Project_Na": r["Project_Na"],
            "description": r["description"],
            "Infrastruc_predicted": r["Infrastruc_predicted"],
            "confidence": r["confidence"],
            "manual_correction": "",
            "correction_notes": "",
            "reasoning": r["reasoning"],
            "raw_response": r["raw_response"],
        }
        for r in results
    ]).to_csv(path, index=False, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify infrastructure type for LMS rows in the Claude-merged CSV.")
    parser.add_argument("--full", "--production", action="store_true", dest="production",
                        help="Classify ALL empty-Infrastruc rows and write a classified CSV.")
    parser.add_argument("--test", action="store_true", help="Test mode: sample rows, review CSV only (default).")
    parser.add_argument("--no-delay", action="store_true", help="Skip the delay between Ollama calls.")
    parser.add_argument("--input", type=Path, default=INPUT_CSV, help="input CSV (default: Claude-merged file)")
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV, help="output CSV for --full (default: Claude-merged classified file)")
    args = parser.parse_args()

    production = args.production
    delay_sec = 0.0 if args.no_delay else DELAY_SECONDS
    input_csv = args.input
    output_csv = args.output

    print(f"Loading definitions from: {DEFINITIONS_JSON}")
    definitions = load_definitions(DEFINITIONS_JSON)
    print(f"  Loaded {len(definitions)} infrastructure type definitions.")

    print(f"Loading dataset from: {input_csv}")
    if not input_csv.exists():
        print(f"Error: input CSV not found: {input_csv}", file=sys.stderr)
        return 1
    df = pd.read_csv(input_csv)
    print(f"  Total rows: {len(df)}")

    if INFRA_COL not in df.columns:
        print(f"Error: '{INFRA_COL}' column not found.", file=sys.stderr)
        return 1

    empty_mask = df[INFRA_COL].apply(is_empty_infra)
    to_classify = [i for i in df.index if empty_mask.loc[i]]
    print(f"  Rows with empty {INFRA_COL}: {len(to_classify)}")

    if not to_classify:
        print("\nNothing to classify — all rows already have an Infrastruc value.")
        return 0

    if production:
        row_indices = to_classify
        print(f"\nProduction mode: classifying all {len(row_indices)} rows.")
    else:
        random.seed(RANDOM_SEED)
        sample_size = min(TEST_SAMPLE_SIZE, len(to_classify))
        row_indices = random.sample(to_classify, sample_size)
        print(f"\nTest mode: classifying {len(row_indices)} sampled rows (review CSV only).")

    print(f"   Model: {OLLAMA_MODEL}  |  examples/label: {N_EXAMPLES_PER_LABEL}  |  delay: {delay_sec}s\n")

    results = run_classification(df, definitions, row_indices, delay_sec=delay_sec)
    print_summary(results)

    if production:
        for r in results:
            df.at[r["df_index"], INFRA_COL] = r["Infrastruc_predicted"]
        df.to_csv(output_csv, index=False, encoding="utf-8")
        print(f"Wrote classified dataset to {output_csv}")
        print(f"  (original input CSV left unchanged: {input_csv})")
        log_path = write_log(results, "production")
        print(f"Audit log written to {log_path}")
    else:
        log_path = write_log(results, "test")
        print(f"Review CSV written to {log_path}")
        print("   Review this file before running with --full.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
