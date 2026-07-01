"""
infra_common.py — shared logic for the infrastructure classifier and its evaluator.
Both scripts import from here so they use the SAME few-shot pool, prompt, and parsing,
which is what guarantees no row is ever both a few-shot example and a graded test row.
"""
from __future__ import annotations
import json, random, re, time
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_CSV   = ROOT / "data" / "Merged Using Claude" / "OurDataset_updated_DESC_summarized.csv"
OUTPUT_CSV  = ROOT / "data" / "Merged Using Claude" / "OurDataset_updated_DESC_INFRA_final.csv"
DEFINITIONS_JSON = ROOT / "data" / "input" / "infrastructure_type_definitions.json"   # optional override
PROFESSOR_REVIEW_XLSX = ROOT / "data" / "reviewed" / "professor_review_infrastructure_2026-06-09.xlsx"
HOSTED_DATASET_CSV = ROOT / "data" / "Merged Using Claude" / "current_dataset_on_tool.csv"
LOG_DIR     = ROOT / "data" / "output" / "logs"
CHECKPOINT_DIR = ROOT / "data" / "output" / "checkpoints"

TITLE_COL = "Project_Na"
SUMMARY_COL = "New_15_25_"     # 15-25 word summary (present on all rows)
DETAIL_COL  = "OLD___Brie"     # long description (often blank on original rows)
INFRA_COL   = "Infrastruc"
SOURCE_COL  = "Source_Dataset"

REVIEW_INDEX_COL = "df_index"
REVIEW_TITLE_COL = "Project_Na"
REVIEW_DESC_COL = "description"
REVIEW_PRED_COL = "Infrastruc_predicted"
REVIEW_NOTE_COL = "correction_notes"
REVIEW_LABEL_ALIASES = {
    "blue": "Blue", "green": "Green", "grey": "Grey", "gray": "Grey", "hybrid": "Hybrid",
}

OLLAMA_MODEL = "qwen3:8b"
N_EXAMPLES_PER_LABEL = 6
RANDOM_SEED = 42
DELAY_SECONDS = 1.0

PASS1_OPTIONS = {"temperature": 0}
PASS2_OPTIONS = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
RECLASSIFY_CONFIDENCES = {"medium", "low"}

ALLOWED_LABELS = ["Blue", "Green", "Grey", "Hybrid"]
DEFINITION_KEY_TO_LABEL = {
    "Blue Infrastructure": "Blue",
    "Green Infrastructure": "Green",
    "Grey Infrastructure": "Grey",
    "Hybrid Infrastructure": "Hybrid",
    "Hybrid": "Hybrid",
}
LONG_DEFINITION_KEY_TO_LABEL = {
    "Blue Infrastructure": "Blue Infrastructure",
    "Green Infrastructure": "Green Infrastructure",
    "Grey Infrastructure": "Grey Infrastructure",
    "Hybrid Infrastructure": "Hybrid",
    "Hybrid": "Hybrid",
}

def safe_str(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)): return ""
    return str(v).strip()

def is_usable_description(desc) -> bool:
    """False when a project has no real description text for few-shot prompting."""
    text = safe_str(desc)
    if not text:
        return False
    lower = re.sub(r"\s+", " ", text.lower()).strip()
    if lower in {"n/a", "na", "none", "null", "tbd", "-", "—", "project details undisclosed"}:
        return False
    unavailable_phrases = (
        "project details undisclosed",
        "details undisclosed",
        "details unavailable",
        "no description available",
        "description not available",
        "description unavailable",
    )
    return not any(phrase in lower for phrase in unavailable_phrases)

def is_empty_infra(v) -> bool:
    return safe_str(v) == ""

def as_review_label(value) -> str | None:
    """Return a canonical label when `value` is exactly one of the four types."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return REVIEW_LABEL_ALIASES.get(str(value).strip().lower())

def is_review_removal(value) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    return "remove" in str(value).strip().lower()

def resolve_professor_review_label(row) -> str | None:
    """Professor-reviewed label, or None when the row is flagged for removal."""
    note = row.get(REVIEW_NOTE_COL)
    if is_review_removal(note):
        return None
    note_label = as_review_label(note)
    if note_label:
        return note_label
    pred = safe_str(row.get(REVIEW_PRED_COL))
    return parse_label(pred) if pred else None

def load_professor_review_rows(review_path: Path | None = None) -> pd.DataFrame:
    path = review_path or PROFESSOR_REVIEW_XLSX
    if not path.exists():
        raise FileNotFoundError(f"Professor review file not found: {path}")
    return pd.read_excel(path, header=1, dtype=str)

def load_professor_review_candidates(review_path: Path | None = None) -> list[dict]:
    """All professor-reviewed LMS rows with resolved labels (removals excluded)."""
    review = load_professor_review_rows(review_path)
    candidates = []
    for _, row in review.iterrows():
        label = resolve_professor_review_label(row)
        if not label:
            continue
        description = safe_str(row.get(REVIEW_DESC_COL))
        if not is_usable_description(description):
            continue
        candidates.append({
            "df_index": int(row[REVIEW_INDEX_COL]),
            "title": safe_str(row.get(REVIEW_TITLE_COL)),
            "description": description,
            "label": label,
            "source": "professor_review",
        })
    return candidates

def order_fewshot_examples(examples: list[dict]) -> list[dict]:
    by = {lab: [e for e in examples if e["label"] == lab] for lab in ALLOWED_LABELS}
    ordered = []
    for blue, hybrid in zip(by["Blue"], by["Hybrid"]):
        ordered += [blue, hybrid]
    seen = {id(e) for e in ordered}
    ordered += [e for e in by["Blue"] + by["Hybrid"] if id(e) not in seen]
    ordered += by["Green"] + by["Grey"]
    return ordered

def load_professor_review_fewshot(
    n_per_label: int = N_EXAMPLES_PER_LABEL,
    seed: int = RANDOM_SEED,
    exclude_indices: set[int] | None = None,
    review_path: Path | None = None,
    *,
    quiet: bool = False,
) -> list[dict]:
    """Balanced few-shot pool from professor-reviewed LMS projects."""
    exclude = exclude_indices or set()
    by_label = {lab: [] for lab in ALLOWED_LABELS}
    for candidate in load_professor_review_candidates(review_path):
        if candidate["df_index"] in exclude:
            continue
        by_label[candidate["label"]].append(candidate)

    rng = random.Random(seed)
    selected = []
    label_counts = {}
    backfill_counts = {lab: 0 for lab in ALLOWED_LABELS}
    for lab in ALLOWED_LABELS:
        pool = by_label[lab][:]
        rng.shuffle(pool)
        take = pool[:n_per_label]

        if len(take) < n_per_label:
            needed = n_per_label - len(take)
            exclude_titles = {c["title"].strip().lower() for c in pool}
            backfill = load_hosted_dataset_candidates(
                lab,
                exclude_titles=exclude_titles,
                prefer_non_lms=(lab == "Green"),
            )
            rng.shuffle(backfill)
            added = backfill[:needed]
            take.extend(added)
            backfill_counts[lab] = len(added)

        selected.extend(take)
        label_counts[lab] = len(take)
        if not quiet and len(take) < n_per_label:
            print(f"  warning: only {len(take)}/{n_per_label} examples for '{lab}' after hosted-dataset backfill")

    if not quiet:
        review_counts = {lab: len(by_label[lab]) for lab in ALLOWED_LABELS}
        print(f"  few-shot examples: {label_counts}")
        if any(backfill_counts.values()):
            print(f"  hosted-dataset backfill added: {backfill_counts}")
        print(f"  professor-review pool available: {review_counts}")
    return order_fewshot_examples(selected)

def normalize_definition_entry(entry) -> dict:
    """Support legacy string values and {definition, examples} objects."""
    if isinstance(entry, str):
        return {"definition": entry.strip(), "examples": []}
    if isinstance(entry, dict):
        return {
            "definition": str(entry.get("definition", "")).strip(),
            "examples": [
                str(example).strip()
                for example in entry.get("examples", [])
                if str(example).strip()
            ],
        }
    return {"definition": str(entry).strip(), "examples": []}


def format_definition_lines(
    key: str,
    entry,
    *,
    label_map: dict[str, str] | None = None,
) -> list[str]:
    """Render a definition paragraph and example list for prompt injection."""
    label = (label_map or DEFINITION_KEY_TO_LABEL).get(key, key)
    normalized = normalize_definition_entry(entry)
    lines = [f"• {label}:", f"  Definition: {normalized['definition']}"]
    if normalized["examples"]:
        lines.append("  Examples:")
        lines.extend(f"    - {example}" for example in normalized["examples"])
    lines.append("")
    return lines


def load_definitions() -> dict:
    if not DEFINITIONS_JSON.exists():
        raise FileNotFoundError(f"Definitions file not found: {DEFINITIONS_JSON}")
    with open(DEFINITIONS_JSON, encoding="utf-8") as f:
        return json.load(f)

def parse_label(raw) -> str:
    if not raw or not isinstance(raw, str): return "Grey"
    l = raw.strip().lower()
    for lab in ALLOWED_LABELS:
        if lab.lower() == l: return lab
    if "hybrid" in l: return "Hybrid"
    if "blue" in l: return "Blue"
    if "green" in l: return "Green"
    if "grey" in l or "gray" in l: return "Grey"
    return "Grey"

def strip_thinking(raw: str) -> str:
    if not raw: return ""
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

def parse_response(raw: str):
    """(label, confidence, reasoning, parse_failed)"""
    cleaned = strip_thinking(raw)
    if not cleaned: return "Grey", "low", "", True
    try:
        clean = cleaned
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"): clean = clean[4:]
        m = re.search(r"\{.*\}", clean.strip(), flags=re.DOTALL)
        if m: clean = m.group(0)
        data = json.loads(clean)
        conf = str(data.get("confidence", "low")).strip().lower()
        if conf not in ("high", "medium", "low"): conf = "low"
        return parse_label(data.get("type", "")), conf, str(data.get("reasoning", "")).strip(), False
    except (json.JSONDecodeError, AttributeError, IndexError):
        return parse_label(cleaned), "low", "", True

def build_description(row) -> str:
    """Combine summary + detail honestly: both when they differ, one when blank/identical."""
    summ = safe_str(row.get(SUMMARY_COL))
    detail = safe_str(row.get(DETAIL_COL))
    if summ and detail and summ != detail:
        return f"Summary: {summ}\nDetail: {detail}"
    return detail or summ or ""

def load_hosted_dataset_candidates(
    label: str,
    *,
    exclude_titles: set[str] | None = None,
    prefer_non_lms: bool = False,
    dataset_path: Path | None = None,
) -> list[dict]:
    """Labeled projects from the dataset currently hosted on the tool."""
    path = dataset_path or HOSTED_DATASET_CSV
    if not path.exists():
        return []

    df = pd.read_csv(path, dtype=str)
    blocked = {t.strip().lower() for t in (exclude_titles or set()) if t}
    candidates = []
    for idx, row in df.iterrows():
        if parse_label(safe_str(row.get(INFRA_COL))) != label:
            continue
        title = safe_str(row.get(TITLE_COL))
        if title.lower() in blocked:
            continue
        description = build_description(row)
        if not is_usable_description(description):
            continue
        is_lms = safe_str(row.get(SOURCE_COL)).upper() == "LMS"
        candidates.append({
            "df_index": int(idx),
            "title": title,
            "description": description,
            "label": label,
            "source": "hosted_dataset",
            "is_lms": is_lms,
        })

    if prefer_non_lms:
        candidates.sort(key=lambda c: c["is_lms"])
    return candidates

def has_both_descriptions(row) -> bool:
    summ, detail = safe_str(row.get(SUMMARY_COL)), safe_str(row.get(DETAIL_COL))
    return bool(summ and detail and summ != detail)

def select_fewshot_pool(df, n_per_label=N_EXAMPLES_PER_LABEL, seed=RANDOM_SEED) -> set:
    """Deterministic, balanced few-shot pool drawn from labeled rows. Returns row indices."""
    labeled = df[df[INFRA_COL].apply(lambda v: not is_empty_infra(v))].copy()
    labeled["_lab"] = labeled[INFRA_COL].map(parse_label)
    pool = []
    for lab in ALLOWED_LABELS:
        sub = labeled[labeled["_lab"] == lab].sample(frac=1.0, random_state=seed)
        pool += list(sub.index[:n_per_label])
    return set(pool)

def build_examples(df, pool_indices) -> list[dict]:
    ex = []
    for idx in pool_indices:
        row = df.loc[idx]
        ex.append({"title": safe_str(row.get(TITLE_COL)),
                   "description": build_description(row),
                   "label": parse_label(safe_str(row.get(INFRA_COL)))})
    return order_fewshot_examples(ex)

def build_prompt(
    definitions,
    examples,
    title,
    description,
    *,
    label_map: dict[str, str] | None = None,
) -> str:
    label_map = label_map or DEFINITION_KEY_TO_LABEL
    type_options = "Blue | Green | Grey | Hybrid"
    lines = [
        "You are an expert classifier for climate resilience and urban infrastructure projects.",
        "Assign exactly one infrastructure type to a project based on its title and description.",
        "",
        "─── INFRASTRUCTURE TYPE DEFINITIONS ───────────────────────────────────────────",
    ]
    for key, entry in definitions.items():
        lines.extend(format_definition_lines(key, entry, label_map=label_map))

    lines += ["─── CLASSIFICATION EXAMPLES ────────────────────────────────────────────────────", ""]
    for ex in examples:
        desc = ex["description"]
        truncated = (desc[:500] + "...") if len(desc) > 500 else desc
        lines += [f"Title: {ex['title']}", f"Description: {truncated}", f"Type: {ex['label']}", ""]

    lines += [
        "─── YOUR TASK ──────────────────────────────────────────────────────────────────",
        "",
        "Classify the project below. Reply with ONLY valid JSON — no extra text, no markdown.",
        "",
        "Respond in this exact format:",
        "{",
        f'  "type": "one of: {type_options}",',
        '  "confidence": "high | medium | low",',
        '  "reasoning": "one concise sentence explaining why you chose this type"',
        "}",
        "",
        f"Title: {title}",
        f"Description: {(description[:1000] + '...') if len(description) > 1000 else description}",
        "",
        "JSON response:",
    ]
    return "\n".join(lines)

def call_ollama(prompt, think=False, options=None, model: str | None = None) -> str:
    from ollama import chat
    kw = {"model": model or OLLAMA_MODEL, "messages": [{"role": "user", "content": prompt}], "options": options or PASS1_OPTIONS}
    try:
        resp = chat(think=think, **kw)
    except TypeError:
        resp = chat(**kw)
    msg = getattr(resp, "message", None)
    return ((getattr(msg, "content", None) or "") if msg else "").strip()

def load_checkpoint(path: Path) -> dict:
    done = {}
    if path.exists():
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            try:
                r = json.loads(line); done[int(r["df_index"])] = r
            except (json.JSONDecodeError, KeyError): continue
    return done

def append_checkpoint(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f: f.write(json.dumps(rec) + "\n")

def run_pass(df, definitions, examples, row_indices, *, think, options, ckpt_path,
             resume, delay_sec, pass_name) -> dict:
    results = load_checkpoint(ckpt_path) if resume else {}
    if results: print(f"  [{pass_name}] resuming — {len(results)} done")
    todo = [i for i in row_indices if i not in results]
    total = len(todo)
    print(f"  [{pass_name}] {total} rows (think={think})")
    for n, idx in enumerate(todo, 1):
        row = df.loc[idx]
        title = safe_str(row.get(TITLE_COL)); desc = build_description(row)
        prompt = build_prompt(definitions, examples, title, desc)
        try:
            raw = call_ollama(prompt, think=think, options=options)
            label, conf, reason, failed = parse_response(raw); err = ""
        except Exception as e:  # noqa: BLE001
            raw, label, conf, reason, failed, err = "", "Grey", "low", "", True, str(e)
        rec = {"df_index": int(idx), "pass": pass_name, "Project_Na": title, "description": desc,
               "Infrastruc_predicted": label, "confidence": conf, "reasoning": reason,
               "parse_failed": failed, "error": err, "raw_response": raw}
        results[idx] = rec; append_checkpoint(ckpt_path, rec)
        print(f"    [{n}/{total}] {title[:46]:<46} -> {label:<6} ({conf}){' !FAIL' if failed else ''}")
        if delay_sec > 0 and n < total: time.sleep(delay_sec)
    return results

def classify_rows(df, row_indices, examples, *, mode, resume, delay_sec, do_pass2):
    """Two-pass classify. Returns {df_index: final_record} with pass1_* fields kept."""
    definitions = load_definitions()
    c1 = CHECKPOINT_DIR / f"{mode}_pass1.jsonl"; c2 = CHECKPOINT_DIR / f"{mode}_pass2.jsonl"
    print("\n=== PASS 1 (thinking OFF) ===")
    p1 = run_pass(df, definitions, examples, row_indices, think=False, options=PASS1_OPTIONS,
                  ckpt_path=c1, resume=resume, delay_sec=delay_sec, pass_name="pass1")
    p2idx = [i for i in row_indices if p1[i]["confidence"] in RECLASSIFY_CONFIDENCES or p1[i]["parse_failed"]]
    p2 = {}
    if p2idx and do_pass2:
        print(f"\n=== PASS 2 (thinking ON) — {len(p2idx)} rows ===")
        p2 = run_pass(df, definitions, examples, p2idx, think=True, options=PASS2_OPTIONS,
                      ckpt_path=c2, resume=resume, delay_sec=delay_sec, pass_name="pass2")
    finals = {}
    for i in row_indices:
        b = dict(p1[i]); b["pass1_label"] = p1[i]["Infrastruc_predicted"]; b["pass1_confidence"] = p1[i]["confidence"]
        b["used_thinking"] = i in p2
        if i in p2:
            b.update({"Infrastruc_predicted": p2[i]["Infrastruc_predicted"], "confidence": p2[i]["confidence"],
                      "reasoning": p2[i]["reasoning"], "parse_failed": p2[i]["parse_failed"],
                      "raw_response": p2[i]["raw_response"]})
        finals[i] = b
    return finals