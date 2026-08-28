"""Ortak yardımcılar: config, run dizinleri, hash, jsonl."""

import hashlib
import json
import os
import time


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


def sha_of(text):
    """Prompt kimliği: metnin sha1'inin ilk 12 hanesi (duplicate-genom önbelleği bunu kullanır)."""
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def run_dir_for(cfg, arm, seed):
    d = os.path.join(cfg.get("results_dir", "results/pilot"), arm, f"seed{seed}")
    ensure_dir(os.path.join(d, "raw"))
    ensure_dir(os.path.join(d, "preds"))
    return d


def append_jsonl(path, row):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S")
