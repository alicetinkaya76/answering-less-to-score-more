#!/usr/bin/env python3
"""Generate paper figures F1-F5 from figure_data.json (verified against archive).

Usage:
    python3 make_figures.py [FIGURE_DATA_JSON] [OUT_DIR]

Both may also be given as the environment variables FG_FIGURE_DATA and FG_FIG_OUT.
FIGURE_DATA_JSON defaults to the figure_data.json sitting next to this script -- the
copy checked into the repository, itself produced by analysis.py from the run archive.
Requires matplotlib (the analysis pipeline itself is standard-library only).
"""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

_HERE = os.path.dirname(os.path.abspath(__file__))

DATA = os.path.expanduser(
    sys.argv[1] if len(sys.argv) > 1
    else os.environ.get("FG_FIGURE_DATA", os.path.join(_HERE, "figure_data.json")))
OUT = os.path.expanduser(
    sys.argv[2] if len(sys.argv) > 2
    else os.environ.get("FG_FIG_OUT", os.path.join(_HERE, "figures")))

if not os.path.isfile(DATA):
    sys.exit(f"figure data not found: {DATA}\n"
             f"run analysis.py first, or pass the path to figure_data.json.")
D = json.load(open(DATA))
os.makedirs(OUT, exist_ok=True)
print(f"data: {DATA}\nout:  {OUT}\n")

# Okabe-Ito colorblind-safe palette
C_OPRO, C_GA, C_WRONG, C_HARD = "#0072B2", "#D55E00", "#009E73", "#CC79A7"
C_BASE = "#000000"
plt.rcParams.update({
    "font.size": 10, "axes.labelsize": 11, "axes.titlesize": 11.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 110, "savefig.dpi": 300, "legend.frameon": False,
})
BASE_DEV = D["fig1"]["baseline_dev"]["fit"]
BASE_TEST = 0.7930

def save(fig, name):
    fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight")
    fig.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("saved", name)

# ---------------------------------------------------------------- F1: coverage-fitness landscape
fig, ax = plt.subplots(figsize=(6.6, 4.4))
op = D["fig1"]["opro"]; ga = D["fig1"]["ga"]
ax.scatter([p["cov"] for p in op], [p["fit"] for p in op], s=34, alpha=0.75,
           color=C_OPRO, marker="o", label=f"OPRO candidates (n={len(op)})", edgecolor="white", linewidth=0.4)
ax.scatter([p["cov"] for p in ga], [p["fit"] for p in ga], s=40, alpha=0.75,
           color=C_GA, marker="^", label=f"GA candidates (n={len(ga)})", edgecolor="white", linewidth=0.4)
ax.axhline(BASE_DEV, color=C_BASE, lw=1, ls="--")
ax.scatter([1.0], [BASE_DEV], marker="*", s=260, color=C_BASE, zorder=5, label="M2 baseline (dev)")
# OPRO bin means
bins = D["fig1"]["opro_bins"]
for (x0, x1, key) in [(0.8, 1.0, "hi"), (0.5, 0.8, "mid"), (0.05, 0.5, "lo")]:
    ax.hlines(bins[key], x0, x1, color=C_BASE, lw=2.4, alpha=0.85)
    ax.annotate(f"{bins[key]:.3f}", ((x0 + x1) / 2, bins[key]),
                textcoords="offset points", xytext=(0, 5), ha="center", fontsize=9, fontweight="bold")
ax.annotate("mean OPRO fitness per coverage bin", (0.28, bins["lo"] + 0.055), fontsize=9, style="italic")
ax.annotate("", xy=(0.30, 0.90), xytext=(0.86, 0.76),
            arrowprops=dict(arrowstyle="->", color="0.35", lw=1.4))
ax.annotate("fitness gradient under $F_{excl}$", (0.44, 0.87), fontsize=9, color="0.25", rotation=-12)
ax.set_xlabel("Coverage (strict parser, dev)")
ax.set_ylabel("Fitness  =  $F_{excl}$  (macro-F1 over parsed items, dev)")
ax.set_xlim(0.0, 1.04); ax.set_ylim(0.28, 1.0)
ax.legend(loc="lower left", fontsize=9)
save(fig, "fig1_coverage_fitness_landscape")

# ---------------------------------------------------------------- F2: generation dynamics
fig, ax = plt.subplots(figsize=(6.6, 4.2))
styles = {11: dict(ls="-", marker="o"), 23: dict(ls="--", marker="s"), 47: dict(ls=":", marker="^")}
regs = [("ga_excl", C_GA, "GA × $F_{excl}$ (strict pipeline)"),
        ("ga_wrong", C_WRONG, "GA × $F_{wrong}$ (strict pipeline)"),
        ("hardened", C_HARD, "GA × $F_{excl}$ (hardened pipeline)")]
for reg, col, lab in regs:
    for i, s in enumerate((11, 23, 47)):
        t = D["fig2"][reg][str(s)]
        ax.plot(t["gens"], t["cov"], color=col, lw=1.8, ms=5, alpha=0.95,
                label=lab if i == 0 else None, **styles[s])
ax.set_xlabel("Generation (0 = initial population)")
ax.set_ylabel("Coverage of the generation's best prompt (strict, dev)")
ax.set_ylim(0.25, 1.05); ax.set_xticks([0, 1, 2, 3, 4])
ax.axhline(1.0, color="0.8", lw=0.8, zorder=0)
leg1 = ax.legend(loc="lower left", fontsize=9)
from matplotlib.lines import Line2D
seed_handles = [Line2D([0], [0], color="0.3", **styles[s], lw=1.5, ms=5, label=f"seed {s}") for s in (11, 23, 47)]
ax.add_artist(leg1)
ax.legend(handles=seed_handles, loc="center left", fontsize=8.5, title="seeds", title_fontsize=8.5)
save(fig, "fig2_generation_dynamics")

# ---------------------------------------------------------------- F3: substance vs artefact
rows = [r for r in D["fig3"] if r["name"] != "M2_HAM"]
labels = {"M2_KISITSIZ": "M2 − 4 words\n(0 evals)", "M8_KISITSIZ": "M8 − 4 words\n(0 evals)",
          "ga_excl_seed11": "GA winner, s11\n(38 evals)", "opro_excl_seed47": "OPRO winner, s47\n(57 evals)"}
fig, ax = plt.subplots(figsize=(6.4, 4.4))
xs = range(len(rows))
for i, r in enumerate(rows):
    sub, art = r["substance"], r["artefact"]
    ax.bar(i, sub, width=0.62, color=(C_WRONG if sub >= 0 else "#B2182B"),
           label="substance (real gain, lenient@256)" if i == 0 else None)
    ax.bar(i, art, width=0.62, bottom=sub, color="0.75", hatch="///", edgecolor="0.35",
           label="artefact (reported − real)" if i == 0 else None)
    top = sub + art
    ax.annotate(f"reported {top:+.3f}", (i, top), textcoords="offset points", xytext=(0, 4),
                ha="center", fontsize=9, fontweight="bold")
    ax.annotate(f"real {sub:+.3f}", (i, min(sub, 0)), textcoords="offset points",
                xytext=(0, -14), ha="center", fontsize=9,
                color=(C_WRONG if sub >= 0 else "#B2182B"), fontweight="bold")
ax.axhline(0, color="k", lw=1)
ax.set_xticks(list(xs)); ax.set_xticklabels([labels[r["name"]] for r in rows], fontsize=9)
ax.set_ylabel("Δ macro-F1 vs. M2 baseline (test)")
ax.set_ylim(-0.09, 0.20)
ax.legend(loc="upper left", fontsize=9)
save(fig, "fig3_substance_vs_artefact")

# ---------------------------------------------------------------- F4: battery heatmap
models = ["qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "llama3.1:8b"]
vectors = ["V1_KISITSIZ", "V2_TEREDDUT", "V3_AKIL_YURUT", "V4_TRANSFER_O", "V5_TRANSFER_G"]
vlabels = ["V1\nconstraint\ndeleted", "V2\n\u201cabstain if\nunsure\u201d", "V3\nreasoning-\ninducing", "V4\ntransfer\n(OPRO win.)", "V5\ntransfer\n(GA win.)"]
bat = {(r["model"], r["vector"]): r for r in D["fig4"]}
ctrl = {m: bat[(m, "V0_KONTROL")]["cov"] for m in models}
import numpy as np
drop = np.array([[max(0.0, ctrl[m] - bat[(m, v)]["cov"]) for v in vectors] for m in models])
fig, ax = plt.subplots(figsize=(7.0, 3.9))
im = ax.imshow(drop, cmap="Reds", vmin=0, vmax=1, aspect="auto")
for i, m in enumerate(models):
    for j, v in enumerate(vectors):
        r = bat[(m, v)]
        dark = drop[i, j] > 0.55
        txt = f"cov {r['cov']:.2f}\nΔF1 {r['d_f1']:+.2f}"
        ax.text(j, i, txt, ha="center", va="center", fontsize=8.6,
                color="white" if dark else "black")
        exploit = (0.05 < r["cov"] < 0.95) and (r["d_f1"] > 0.05)
        if exploit:
            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=C_GA, lw=3))
ax.set_xticks(range(len(vectors))); ax.set_xticklabels(vlabels, fontsize=8.6)
ax.set_yticks(range(len(models))); ax.set_yticklabels(models, fontsize=9.5)
cb = fig.colorbar(im, ax=ax, shrink=0.85)
cb.set_label("coverage drop vs. control prompt", fontsize=9)
ax.set_title("Escape-vector battery (n=300, strict parser, np=24) — boxed cells: exploitable regime", fontsize=10)
save(fig, "fig4_battery_heatmap")

# ---------------------------------------------------------------- F5: honest accounting per manipulated run
runs = ["opro_excl/11", "opro_excl/23", "opro_excl/47", "ga_excl/11", "ga_excl/23", "ga_excl/47"]
rlab = [(f"OPRO s{r.split('/')[1]}" if "opro" in r else f"GA s{r.split('/')[1]}")
        + f"\ncov {D['fig5'][r]['coverage']:.2f}" for r in runs]
rep = [D["fig5"][r]["reported"] for r in runs]
fw = [D["fig5"][r]["f_wrong"] for r in runs]
fo = [D["fig5"][r]["forced"] for r in runs]
cov = [D["fig5"][r]["coverage"] for r in runs]
x = np.arange(len(runs)); w = 0.27
fig, ax = plt.subplots(figsize=(7.2, 4.3))
ax.bar(x - w, rep, w, color="0.25", label="reported ($F_{excl}$, strict@24)")
ax.bar(x, fo, w, color=C_OPRO, alpha=0.9, label="forced-answer (constraint restored)")
ax.bar(x + w, fw, w, color=C_WRONG, alpha=0.95, label="honest ($F_{wrong}$, strict@24)")
real = D["fig5_real_loose256"]
for r, xx in zip(runs, x):
    if r in real:
        ax.scatter([xx - w], [real[r]], marker="D", s=52, color="#F0E442",
                   edgecolor="k", zorder=6,
                   label="real (lenient@256)" if r == "ga_excl/11" else None)
ax.axhline(BASE_TEST, color="k", ls="--", lw=1.2)
ax.annotate("M2 baseline 0.793", (5.35, BASE_TEST), textcoords="offset points", xytext=(0, 5),
            ha="right", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(rlab, fontsize=9.5)
ax.set_ylabel("macro-F1 (test)")
ax.set_ylim(0, 1.02)
ax.legend(loc="upper right", fontsize=8.6, ncol=2)
save(fig, "fig5_honest_accounting")
print("done")
