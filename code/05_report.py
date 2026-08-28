#!/usr/bin/env python3
"""Görev 7 — GİT/GİTME karar raporu: results/pilot/REPORT.md + report.json."""
import os

from fg.cli import base_argparser
from fg.common import load_config
from fg.report import build_report


def main():
    ap = base_argparser(__doc__)
    args = ap.parse_args()
    cfg = load_config(args.config)
    baselines = os.path.join(cfg["results_dir"], "baselines", "baselines.json")
    if not os.path.exists(baselines):
        raise SystemExit("Önce 02_run_baselines.py koşulmalı (baseline yok).")
    gates, _ = build_report(cfg, baselines)
    print(f"Rapor yazıldı: {os.path.join(cfg['results_dir'], 'REPORT.md')}")
    for name, g in gates.items():
        print(f"  {name}: {'GEÇTİ' if g['pass'] else 'GEÇMEDİ'} — {g['detail']}")


if __name__ == "__main__":
    main()
