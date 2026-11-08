"""Clean teacher-labelled shard outputs.

Filters raw responses according to the specification:
(a) replies that are not valid JSON;
(b) replies whose keys are not exactly intent, date, time, and place;
(c) replies whose intent is not one of the eight;
(d) replies with a slot value that is neither null nor text that appears in the command;
(e) duplicate commands (keep the one with the smallest id).

Writes cleaned records to datasets/v1/train.jsonl and its SHA-256 to datasets/v1/train.sha256.
Outputs the exact count table required for the report.
"""
import glob
import hashlib
import json
import os
import sys

ALLOWED_KEYS = {"intent", "date", "time", "place"}
ALLOWED_INTENTS = {
    "alarm_set",
    "alarm_query",
    "calendar_set",
    "calendar_query",
    "calendar_remove",
    "weather_query",
    "datetime_query",
    "recommendation_events",
}

SHARDS_DIR = os.environ.get("SHARDS_DIR", "datasets/teacher")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "datasets/v1")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "train.jsonl")
CHECKSUM_FILE = os.path.join(OUTPUT_DIR, "train.sha256")


def normalize_text(s):
    if s is None:
        return None
    return " ".join(str(s).strip().lower().split())


def clean_shards():
    shard_files = sorted(glob.glob(os.path.join(SHARDS_DIR, "shard-*.jsonl")))
    if not shard_files:
        print(f"Error: No shard files found in {SHARDS_DIR}", file=sys.stderr)
        sys.exit(1)

    all_records = []
    for sf in shard_files:
        with open(sf, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    all_records.append(json.loads(line))

    # Keep records in id order
    all_records.sort(key=lambda r: r["id"])

    total_input = len(all_records)
    count_a = 0  # not valid JSON
    count_b = 0  # keys not exactly intent, date, time, place
    count_c = 0  # intent not one of the eight
    count_d = 0  # slot value not null and not appearing in command text
    count_dupes = 0  # duplicate commands
    kept_records = []

    seen_command_texts = set()

    for rec in all_records:
        raw = rec.get("teacher_raw", "")
        cmd_text = rec.get("text", "")
        norm_cmd = normalize_text(cmd_text)

        # Check (a): valid JSON
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(parsed, dict):
                count_a += 1
                continue
        except Exception:
            count_a += 1
            continue

        # Check (b): keys exactly intent, date, time, place
        if set(parsed.keys()) != ALLOWED_KEYS:
            count_b += 1
            continue

        # Check (c): intent is one of the eight
        if parsed.get("intent") not in ALLOWED_INTENTS:
            count_c += 1
            continue

        # Check (d): slot value neither null nor text that appears in command
        slot_error = False
        for slot in ("date", "time", "place"):
            val = parsed.get(slot)
            if val is not None:
                if not isinstance(val, str):
                    slot_error = True
                    break
                norm_val = normalize_text(val)
                if norm_val not in norm_cmd:
                    slot_error = True
                    break
        if slot_error:
            count_d += 1
            continue

        # Check (e): duplicate commands (keep smallest id)
        if norm_cmd in seen_command_texts:
            count_dupes += 1
            continue
        seen_command_texts.add(norm_cmd)

        # Record passes all filters
        kept_records.append({
            "id": rec["id"],
            "text": cmd_text,
            "teacher_reply": parsed
        })

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in kept_records:
            f.write(json.dumps(r) + "\n")

    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(OUTPUT_FILE, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    sha256_hash = hasher.hexdigest()

    with open(CHECKSUM_FILE, "w", encoding="utf-8") as f:
        f.write(f"{sha256_hash}  train.jsonl\n")

    kept_count = len(kept_records)

    print("=" * 60)
    print("DATASET CLEANING SUMMARY TABLE")
    print("=" * 60)
    print(f"Total Input Records       : {total_input}")
    print(f"Rejected (a) Invalid JSON : {count_a}")
    print(f"Rejected (b) Wrong Keys   : {count_b}")
    print(f"Rejected (c) Wrong Intent : {count_c}")
    print(f"Rejected (d) Invalid Slot : {count_d}")
    print(f"Rejected (e) Duplicates   : {count_dupes}")
    print(f"Records Kept (Cleaned)    : {kept_count}")
    print("-" * 60)
    sum_check = count_a + count_b + count_c + count_d + count_dupes + kept_count
    print(f"Sum of parts              : {sum_check} (Matches Total Input: {sum_check == total_input})")
    print(f"Output File               : {OUTPUT_FILE}")
    print(f"SHA-256 Checksum          : {sha256_hash}")
    print("=" * 60)


if __name__ == "__main__":
    clean_shards()
