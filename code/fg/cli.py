"""Runner script'lerinin ortak açılış kodu."""

import argparse
import json
import os

from .common import ensure_dir, load_config, now_iso, write_json
from .data import load_dataset, make_or_load_splits
from .llm import OllamaClient
from .mockllm import MockClient


def base_argparser(desc):
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--mock", action="store_true",
                    help="Ollama'sız kuru koşu (yalnız harness doğrulaması; gerçek deney değil)")
    ap.add_argument("--seeds", type=int, nargs="*", default=None,
                    help="config.seeds yerine kullanılacak seed listesi")
    return ap


def bootstrap(args):
    cfg = load_config(args.config)
    client = MockClient() if args.mock else OllamaClient(
        cfg.get("ollama_url", "http://localhost:11434"),
        timeout=int(cfg.get("timeout_s", 180)))
    if not args.mock:
        try:
            models = client.check()
        except Exception as e:
            raise SystemExit(
                f"Ollama sunucusuna ulaşılamadı ({cfg.get('ollama_url')}): {e}\n"
                f"`ollama serve` çalışıyor mu? Model çekildi mi? "
                f"(ollama pull {cfg['target_model']})")
        for m in {cfg["target_model"], cfg.get("optimizer_model", cfg["target_model"])}:
            if m not in models:
                raise SystemExit(f"Model kurulu değil: {m} — `ollama pull {m}`")
    items = load_dataset(cfg["data"])
    dev, test = make_or_load_splits(items, cfg["data"])
    manuals = load_manual_prompts(cfg)
    return cfg, client, dev, test, manuals


def load_manual_prompts(cfg):
    path = cfg.get("manual_prompts_file", "prompts_manual.json")
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return [d[k] for k in sorted(d.keys())]


def snapshot_config(cfg, client, run_dir, extra=None):
    snap = {
        "ts": now_iso(),
        "target_model": cfg["target_model"],
        "optimizer_model": cfg.get("optimizer_model", cfg["target_model"]),
        "target_digest": client.digest(cfg["target_model"]),
        "optimizer_digest": client.digest(cfg.get("optimizer_model", cfg["target_model"])),
        "same_model_condition": cfg["target_model"] == cfg.get("optimizer_model",
                                                               cfg["target_model"]),
        "decoding": cfg.get("decoding"),
        "optimizer_decoding": cfg.get("optimizer_decoding"),
        "data": cfg.get("data"),
        "ga": cfg.get("ga"),
        "opro": cfg.get("opro"),
    }
    if extra:
        snap.update(extra)
    ensure_dir(run_dir)
    write_json(os.path.join(run_dir, "config.json"), snap)
    return snap
