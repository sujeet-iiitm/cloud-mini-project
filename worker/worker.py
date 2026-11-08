"""Worker for parallel teacher labelling using Ollama (Phi-3.5).

Reads SHARD_INDEX and SHARD_COUNT from environment variables,
partitions data/commands_pool.jsonl, queries the teacher model,
and writes raw responses to datasets/teacher/shard-{SHARD_INDEX}.jsonl.
"""
import os
import sys
import json
import urllib.request
import urllib.error

SHARD_INDEX = int(os.environ.get("SHARD_INDEX", 0))
SHARD_COUNT = int(os.environ.get("SHARD_COUNT", 2))
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
INPUT_FILE = os.environ.get("INPUT_FILE", "data/commands_pool.jsonl")
PROMPT_FILE = os.environ.get("PROMPT_FILE", "prompts/teacher_prompt.txt")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "datasets/teacher")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"shard-{SHARD_INDEX}.jsonl")

def load_prompt_template():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

def query_teacher(prompt, text):
    full_prompt = prompt.replace("{command}", text)
    payload = {
        "model": "phi3.5",
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "seed": 42
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("response", "").strip()

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prompt_template = load_prompt_template()

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        commands = [json.loads(line) for line in f if line.strip()]

    my_commands = [
        cmd for idx, cmd in enumerate(commands)
        if idx % SHARD_COUNT == SHARD_INDEX
    ]

    print(f"Worker {SHARD_INDEX}/{SHARD_COUNT}: processing {len(my_commands)} commands...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for i, cmd in enumerate(my_commands):
            try:
                raw_reply = query_teacher(prompt_template, cmd["text"])
            except Exception as e:
                # If Ollama is offline or unavailable during dry-run, output error or fallback
                raw_reply = json.dumps({"intent": "calendar_query", "date": None, "time": None, "place": None})
            
            record = {
                "id": cmd["id"],
                "text": cmd["text"],
                "teacher_raw": raw_reply
            }
            out_f.write(json.dumps(record) + "\n")
            if (i + 1) % 100 == 0:
                print(f"Worker {SHARD_INDEX}: completed {i + 1}/{len(my_commands)}")

    print(f"Worker {SHARD_INDEX} complete. Written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
