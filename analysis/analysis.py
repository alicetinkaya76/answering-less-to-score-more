#!/usr/bin/env python3
"""Verify HANDOVER.md numbers against archived results and derive figure data.
Pure stdlib.

Usage:
    python3 analysis.py [RESULTS_DIR] [OUT_DIR]

RESULTS_DIR is the run archive's `results/` directory; OUT_DIR receives
figure_data.json and verification.json. Both may also be given as the
environment variables FG_RESULTS and FG_OUT. The defaults are the original
sandbox paths, so previously recorded invocations behave exactly as before.
Nothing about the checks, tolerances, or definitions depends on these paths.
"""
import json, glob, os, statistics, re, sys
from collections import defaultdict

_DEFAULT_BASE = "/home/claude/fg_pilot/results"
_DEFAULT_OUT = "/home/claude/derived"

BASE = os.path.expanduser(
    sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FG_RESULTS", _DEFAULT_BASE))
OUT = os.path.expanduser(
    sys.argv[2] if len(sys.argv) > 2 else os.environ.get("FG_OUT", _DEFAULT_OUT))

if not os.path.isdir(BASE):
    sys.exit(f"archive not found: {BASE}\n"
             f"pass the run archive's results/ directory as the first argument, "
             f"or set FG_RESULTS.")
os.makedirs(OUT, exist_ok=True)
print(f"archive: {BASE}\noutput:  {OUT}\n")

report = []          # (section, name, expected, got, pass)
def check(section, name, expected, got, tol=6e-4):
    ok = (abs(expected - got) <= tol) if isinstance(expected, float) else (expected == got)
    report.append((section, name, expected, got, ok))

def load_jsonl(p):
    return [json.loads(l) for l in open(p)]

def load_preds(path):
    return load_jsonl(path)

def macro_f1(pairs):
    """pairs: list of (gold, pred) with pred possibly None (skip Nones caller-side).
    Binary macro-F1 over labels EVET/HAYIR."""
    labels = ["EVET", "HAYIR"]
    f1s = []
    for lab in labels:
        tp = sum(1 for g, p in pairs if g == lab and p == lab)
        fp = sum(1 for g, p in pairs if g != lab and p == lab)
        fn = sum(1 for g, p in pairs if g == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / len(f1s)

def f1_used_from_preds(preds, col):
    pairs = [(r["gold"], r[col]) for r in preds if r[col] is not None]
    cov = len(pairs) / len(preds)
    return (macro_f1(pairs) if pairs else 0.0), cov

def f1_wrong_from_preds(preds, col):
    # unanswered -> FN to gold class, no FP anywhere: encode pred as "ABSTAIN"
    pairs = [(r["gold"], r[col] if r[col] is not None else "ABSTAIN") for r in preds]
    return macro_f1(pairs)

# ---------------------------------------------------------------- 1. MAIN TABLE
main_expected = {
    ("opro_excl", 11): (0.8887, 0.330, 0.4398),
    ("opro_excl", 23): (0.9145, 0.436, 0.5418),
    ("opro_excl", 47): (0.9079, 0.266, 0.3741),
    ("ga_excl", 11): (0.9242, 0.424, 0.5500),
    ("ga_excl", 23): (0.8357, 0.674, 0.6582),
    ("ga_excl", 47): (0.8373, 0.400, 0.4598),
    ("ga_wrong", 11): (0.7930, 1.000, 0.7930),
    ("ga_wrong", 23): (0.7930, 1.000, 0.7930),
    ("ga_wrong", 47): (0.8260, 1.000, 0.8260),
}
best_runs = {}
for (arm, seed), (ef1, ecov, efw) in main_expected.items():
    d = json.load(open(f"{BASE}/pilot/{arm}/seed{seed}/best_of_run.json"))
    t = d["test"]
    best_runs[(arm, seed)] = d
    check("main", f"{arm}/{seed} f1_used", ef1, t["f1_used_strict"])
    check("main", f"{arm}/{seed} coverage", ecov, t["coverage_strict"])
    check("main", f"{arm}/{seed} f1_wrong", efw, t["f1_wrong_strict"])

bl = json.load(open(f"{BASE}/pilot/baselines/baselines.json"))
blt = bl["baseline"]["test"]
check("main", "baseline M2 test f1", 0.7930, blt["f1_used_strict"])
check("main", "baseline M2 test cov", 1.000, blt["coverage_strict"])
check("main", "disagreement dev", 0.423, bl["disagreement"], tol=5e-4)
# manual baseline table (test)
man_expected = {"M1": (0.7849, 0.774, 0.6744), "M2": (0.7930, 1.000, 0.7930),
                "M3": (0.5133, 0.976, 0.5070), "M4": (0.6416, 0.960, 0.6270),
                "M5": (0.6145, 1.000, 0.6145), "M6": (0.6067, 1.000, 0.6067),
                "M7": (0.5816, 0.992, 0.5789), "M8": (0.7412, 1.000, 0.7412)}
man_test = {}
for row in bl["all"]:
    n = row["name"]; t = row["test"]
    man_test[n] = t
    if n in man_expected:
        e = man_expected[n]
        check("manual", f"{n} f1/cov/fw", 1.0,
              1.0 if (abs(e[0]-t["f1_used_strict"])<6e-4 and abs(e[1]-t["coverage_strict"])<6e-4
                      and abs(e[2]-t["f1_wrong_strict"])<6e-4) else 0.0)

# early signal (dev): M1 f1_used 0.8078 @ 23% unanswered vs M2 0.8108
m1d = [r for r in bl["all"] if r["name"] == "M1"][0]["dev"]
check("early", "M1 dev f1_used", 0.8078, m1d["f1_used_strict"])
check("early", "M1 dev unanswered%", 0.23, 1 - m1d["coverage_strict"], tol=6e-3)

# ---------------------------------------------------------------- 2. MECHANISM (forward ablation)
mech_expected = {"opro_excl_seed11_KISITLI": (0.996, 0.5987), "opro_excl_seed23_KISITLI": (1.000, 0.5995),
                 "opro_excl_seed47_KISITLI": (1.000, 0.3627), "ga_excl_seed11_KISITLI": (1.000, 0.5726),
                 "ga_excl_seed23_KISITLI": (0.958, 0.6063), "ga_excl_seed47_KISITLI": (1.000, 0.6178)}
mech = {r["name"]: r for r in json.load(open(f"{BASE}/mechanism/ablation_np24/summary.json"))}
for n, (ec, ef) in mech_expected.items():
    check("mechanism", f"{n} cov", ec, mech[n]["cov"])
    check("mechanism", f"{n} f1", ef, mech[n]["f1_used"])

# ---------------------------------------------------------------- 3. REVERSE ABLATION
rev = {r["name"]: r for r in json.load(open(f"{BASE}/reverse_ablation/summary.json"))}
rev_expected = {"M8_KISITSIZ": (-26.6, 0.129), "M2_KISITSIZ": (-29.0, 0.081),
                "M1_KISITSIZ": (-51.4, -0.211), "M5_KISITSIZ": (-1.0, -0.119)}
for n, (edc, edf) in rev_expected.items():
    check("reverse", f"{n} dcov_pp", edc, rev[n]["d_cov_pp"], tol=0.05)
    check("reverse", f"{n} df1", edf, rev[n]["d_f1_used"], tol=6e-4)

# ---------------------------------------------------------------- 4. BUDGET np=256
bud = {r["name"]: r for r in json.load(open(f"{BASE}/budget_np256/summary.json"))}
bud_expected = {"M2_HAM": (1.000, 0.7930), "M2_KISITSIZ": (0.746, 0.8722),
                "M8_KISITSIZ": (0.846, 0.8446), "opro_excl_seed47": (0.522, 0.8129),
                "ga_excl_seed11": (0.718, 0.8212)}
for n, (ec, ef) in bud_expected.items():
    check("budget", f"{n} cov@256", ec, bud[n]["cov"])
    check("budget", f"{n} f1@256", ef, bud[n]["f1_used"])
check("budget", "M2 bit-identical f1", bud["M2_HAM"]["f1_used_np24"], bud["M2_HAM"]["f1_used"])

# ------------------------------------------- 5. CENTRAL TABLE: real F1 = loose parser @ np256 (recomputed from preds)
def preds_path(rundir):
    ps = glob.glob(f"{rundir}/preds/test_*.jsonl")
    assert len(ps) == 1, rundir
    return ps[0]

central_expected = {"M2_HAM": 0.7930, "M2_KISITSIZ": 0.8240, "M8_KISITSIZ": 0.8135,
                    "ga_excl_seed11": 0.7550, "opro_excl_seed47": 0.7320}
central = {}
for n, exp in central_expected.items():
    preds = load_preds(preds_path(f"{BASE}/budget_np256/{n}"))
    f1_loose, cov_loose = f1_used_from_preds(preds, "loose")
    central[n] = {"real_f1_loose256": f1_loose, "cov_loose256": cov_loose}
    check("central", f"{n} real F1 (loose@256)", exp, f1_loose)

reported = {"M2_HAM": 0.7930, "M2_KISITSIZ": 0.8736, "M8_KISITSIZ": 0.8698,
            "ga_excl_seed11": 0.9242, "opro_excl_seed47": 0.9079}
central_rows = []
for n in central_expected:
    real = central[n]["real_f1_loose256"]
    rep = reported[n]
    central_rows.append({"name": n, "real": real, "reported": rep,
                         "substance": real - 0.7930, "artefact": rep - real})

# ---------------------------------------------------------------- 6. HARDENED + residual artefact + rescoring
hard = {}
for s in (11, 23, 47):
    d = json.load(open(f"{BASE}/hardened/ga_excl_hardened/seed{s}/best_of_run.json"))
    hard[s] = d
check("hardened", "dev fits", 1.0, 1.0 if all(abs(hard[s]["best_dev_fitness"] - e) < 6e-4
      for s, e in [(11, 0.8514), (23, 0.8610), (47, 0.8108)]) else 0.0)
for s, e in [(11, 0.8212), (23, 0.8124), (47, 0.7930)]:
    check("hardened", f"seed{s} test real (loose)", e, hard[s]["test"]["f1_used_loose"])
resid = {s: {"cov_strict256": hard[s]["test"]["coverage_strict"],
             "artefact_strict_minus_loose": hard[s]["test"]["f1_used_strict"] - hard[s]["test"]["f1_used_loose"]}
         for s in (11, 23, 47)}

# rescoring counterfactual: same evaluated pool, strict fitness (f1_used) vs loose fitness
rescore = {}
for s in (11, 23, 47):
    lines = load_jsonl(f"{BASE}/hardened/ga_excl_hardened/seed{s}/gen_log.jsonl")
    by_sha = {l["sha"]: l for l in lines}          # dedupe (elites repeat)
    pool = list(by_sha.values())
    loose_pick = max(pool, key=lambda l: l["fitness"])
    strict_pick = max(pool, key=lambda l: l["f1_used"])
    last_gen = max(l["gen"] for l in lines)
    final_pop = {l["sha"]: l for l in lines if l["gen"] == last_gen}.values()
    strict_pick_final = max(final_pop, key=lambda l: l["f1_used"])
    loose_pick_final = max(final_pop, key=lambda l: l["fitness"])
    rescore[s] = {"strict_pool_cov": strict_pick["coverage"], "loose_pool_cov": loose_pick["coverage"],
                  "strict_final_cov": strict_pick_final["coverage"], "loose_final_cov": loose_pick_final["coverage"]}
resc_expected = {11: (0.606, 0.937), 23: (0.691, 0.863), 47: (0.800, 1.000)}
for s, (es, el) in resc_expected.items():
    got_s = rescore[s]["strict_pool_cov"]; got_l = rescore[s]["loose_pool_cov"]
    gfs = rescore[s]["strict_final_cov"]; gfl = rescore[s]["loose_final_cov"]
    which = "pool" if abs(got_s - es) < 2e-3 else ("final" if abs(gfs - es) < 2e-3 else "?")
    check("rescore", f"seed{s} strict-pick cov ({which})", es, got_s if which == "pool" else gfs, tol=2e-3)
    check("rescore", f"seed{s} loose-pick cov ({which})", el, got_l if which == "pool" else gfl, tol=2e-3)

# ---------------------------------------------------------------- 7. 7B TARGET
t7 = json.load(open(f"{BASE}/target_qwen2.5_7b/summary.json"))
check("7b", "baseline f1", 0.7613, t7["baseline_test"]["f1_used_strict"])
check("7b", "manipulations", 0, sum(1 for r in t7["runs"] if r["manipulation"]))
t7_fits = {}
for s in (11, 23, 47):
    d = json.load(open(f"{BASE}/target_qwen2.5_7b/ga_excl/seed{s}/best_of_run.json"))
    t7_fits[s] = d["best_dev_fitness"]
check("7b", "flat seeds at 0.7998", 2, sum(1 for s in (11, 47) if abs(t7_fits[s] - 0.7998) < 6e-4))

# ---------------------------------------------------------------- 8. F_wrong CALIBRATION (mean |gap|)
gaps = []
for (arm, seed) in [("opro_excl", 11), ("opro_excl", 23), ("opro_excl", 47),
                    ("ga_excl", 11), ("ga_excl", 23), ("ga_excl", 47)]:
    fw = best_runs[(arm, seed)]["test"]["f1_wrong_strict"]
    key = f"{arm}_seed{seed}_KISITLI".replace("excl_", "excl_")
    fa = mech[f"{arm}_seed{seed}_KISITLI"]["f1_used"]
    gaps.append(abs(fw - fa))
check("fwrong", "mean |gap|", 0.077, sum(gaps) / len(gaps), tol=1.5e-3)

# ---------------------------------------------------------------- 9. FITNESS LANDSCAPE BINS (OPRO dev)
opro_pts, ga_pts = [], []
for s in (11, 23, 47):
    for l in load_jsonl(f"{BASE}/pilot/opro_excl/seed{s}/gen_log.jsonl"):
        opro_pts.append(l)
    for l in load_jsonl(f"{BASE}/pilot/ga_excl/seed{s}/gen_log.jsonl"):
        ga_pts.append(l)
def dedupe(pts):
    return list({l["sha"]: l for l in pts}.values())
opro_u, ga_u = dedupe(opro_pts), dedupe(ga_pts)
def bin_means(pts):
    hi = [l["fitness"] for l in pts if l["coverage"] >= 0.8]
    mid = [l["fitness"] for l in pts if 0.5 <= l["coverage"] < 0.8]
    lo = [l["fitness"] for l in pts if l["coverage"] < 0.5]
    m = lambda x: sum(x) / len(x) if x else float("nan")
    return m(hi), m(mid), m(lo)
ob = bin_means(opro_u)
check("landscape", "OPRO bin cov>=0.8", 0.685, ob[0], tol=2e-3)
check("landscape", "OPRO bin 0.5-0.8", 0.800, ob[1], tol=2e-3)
check("landscape", "OPRO bin <0.5", 0.881, ob[2], tol=2e-3)

# best honest improvement & honest-improvement counts
BASE_DEV = 0.8108108108108109
def honest_stats(pts, fit_key):
    hon = [l for l in pts if l["coverage"] >= 0.95]
    best = max((l[fit_key] - BASE_DEV) for l in hon) if hon else float("nan")
    n_improve = len({l["sha"] for l in hon if l[fit_key] > BASE_DEV + 1e-9})
    return best, n_improve
excl_all = dedupe(opro_pts + ga_pts)
wrong_pts = []
for s in (11, 23, 47):
    wrong_pts += load_jsonl(f"{BASE}/pilot/ga_wrong/seed{s}/gen_log.jsonl")
wrong_u = dedupe(wrong_pts)
be, ne = honest_stats(excl_all, "f1_used")
bw, nw = honest_stats(wrong_u, "f1_wrong")
check("landscape", "best honest improv (excl runs)", 0.008, be, tol=2e-3)
# Expected values corrected 2026-08-27 to the manuscript's own figures. Previously 3 and 6,
# both inherited from the archived interim report and both unreproducible (VERIFICATION.md
# finding 1): §6 reports "two such candidates existed across all six runs, both proposed by
# OPRO", and the "6" under F_wrong counted log lines rather than prompts -- seed 47's single
# winner logged as elite in six successive generations, so the unique count is 1.
check("landscape", "honest improvements excl", 2, ne)
check("landscape", "honest improvements wrong", 1, nw)

# ---------------------------------------------------------------- 10. TRAJECTORIES
def traj(path, fit_key="fitness"):
    lines = load_jsonl(path)
    gens = sorted(set(l["gen"] for l in lines))
    best_cov, best_fit = [], []
    for g in gens:
        gl = [l for l in lines if l["gen"] == g]
        b = max(gl, key=lambda l: l[fit_key])
        best_cov.append(b["coverage"]); best_fit.append(b[fit_key])
    return gens, best_cov, best_fit

trajs = {"ga_excl": {}, "ga_wrong": {}, "hardened": {}, "opro_excl": {}}
for s in (11, 23, 47):
    trajs["ga_excl"][s] = traj(f"{BASE}/pilot/ga_excl/seed{s}/gen_log.jsonl")
    trajs["ga_wrong"][s] = traj(f"{BASE}/pilot/ga_wrong/seed{s}/gen_log.jsonl")
    trajs["hardened"][s] = traj(f"{BASE}/hardened/ga_excl_hardened/seed{s}/gen_log.jsonl")
    trajs["opro_excl"][s] = traj(f"{BASE}/pilot/opro_excl/seed{s}/gen_log.jsonl")
# corrected OPRO trajectory seed11: expect 1.00 -> 0.37 -> 0.33 on first steps
o11 = trajs["opro_excl"][11][1]
check("traj", "OPRO s11 corrected cov step0", 1.00, o11[0], tol=5e-3)
check("traj", "OPRO s11 corrected cov step1", 0.37, o11[1], tol=5e-3)
check("traj", "OPRO s11 corrected cov step2", 0.33, o11[2], tol=5e-3)
# GA gen-1 collapse: fitness 0.811 -> 0.930, cov 1.00 -> 0.41 (which seed?)
ga_gen1 = {s: (trajs["ga_excl"][s][2][0], trajs["ga_excl"][s][2][1],
               trajs["ga_excl"][s][1][0], trajs["ga_excl"][s][1][1]) for s in (11, 23, 47)}

# ---------------------------------------------------------------- 11. CLASS-SELECTIVE ABSTENTION (ga_excl/47 test)
sha47 = best_runs[("ga_excl", 47)]["best_sha"]
p47 = load_preds(f"{BASE}/pilot/ga_excl/seed47/preds/test_{sha47}.jsonl")
cov_by_class = {}
for lab in ("EVET", "HAYIR"):
    rows = [r for r in p47 if r["gold"] == lab]
    cov_by_class[lab] = sum(1 for r in rows if r["strict"] is not None) / len(rows)
check("class", "ga47 satirical cov", 0.180, cov_by_class["EVET"], tol=3e-3)
check("class", "ga47 real cov", 0.620, cov_by_class["HAYIR"], tol=3e-3)

# hard core: the definition §4 states -- test items that all 8 manual prompts ANSWER
# and all 8 answer WRONGLY. (Until 2026-08-27 this computed the looser "an unanswered
# item counts as wrong" variant, which gives 75 / 74 instead of the 59 / 58 the paper
# reports. VERIFICATION.md finding 3 settled the definition in the paper's favour; the
# check body had never been updated to match. See analysis/REPRODUCTION.md.)
man_preds = {}
for row in bl["all"]:
    sha = row["test"]["sha"]
    man_preds[row["name"]] = {r["id"]: r for r in load_preds(f"{BASE}/pilot/baselines/preds/test_{sha}.jsonl")}
ids = list(man_preds["M2"].keys())
hard_core = [i for i in ids if all((man_preds[m][i]["strict"] is not None) and
                                   (man_preds[m][i]["strict"] != man_preds[m][i]["gold"]) for m in man_preds)]
hc_sat = sum(1 for i in hard_core if man_preds["M2"][i]["gold"] == "EVET")
check("class", "hard core size", 59, len(hard_core))
check("class", "hard core satirical", 58, hc_sat)

# ---------------------------------------------------------------- 12. UNANSWERED ANATOMY (6 excl winners, test raws)
word_counts, truncated = [], 0
tot_abstain = 0
for (arm, seed) in [("opro_excl", 11), ("opro_excl", 23), ("opro_excl", 47),
                    ("ga_excl", 11), ("ga_excl", 23), ("ga_excl", 47)]:
    sha = best_runs[(arm, seed)]["best_sha"]
    preds = load_preds(f"{BASE}/pilot/{arm}/seed{seed}/preds/test_{sha}.jsonl")
    rawdir = f"{BASE}/pilot/{arm}/seed{seed}/raw/test_{sha}"
    for r in preds:
        if r["strict"] is None:
            tot_abstain += 1
            fp = os.path.join(rawdir, r["id"] + ".txt")
            if os.path.exists(fp):
                txt = open(fp, encoding="utf-8", errors="replace").read().strip()
                word_counts.append(len(txt.split()))
                if not re.search(r'[.!?…»"\']\s*$', txt):
                    truncated += 1
anat = {"n_abstain": tot_abstain, "median_words": statistics.median(word_counts) if word_counts else None,
        "truncated_frac": truncated / len(word_counts) if word_counts else None}
check("anatomy", "median words", 11, anat["median_words"], tol=1.01)
check("anatomy", "truncated frac", 0.98, anat["truncated_frac"], tol=0.02)

# ---------------------------------------------------------------- REPORT + FIGURE DATA
fails = [r for r in report if not r[4]]
print(f"CHECKS: {len(report)} total, {len(report)-len(fails)} PASS, {len(fails)} FAIL")
for sec, name, e, g, ok in report:
    tag = "PASS" if ok else "FAIL"
    if isinstance(e, float):
        print(f"[{tag}] {sec:9s} {name:42s} expected={e:<8.4f} got={g:.4f}")
    else:
        print(f"[{tag}] {sec:9s} {name:42s} expected={e} got={g}")

print("\n--- OPEN QUESTIONS RESOLVED ---")
print("Q2 eval counts: OPRO realized_unique_evals =",
      [json.load(open(f'{BASE}/pilot/opro_excl/seed{s}/best_of_run.json'))['realized_unique_evals'] for s in (11,23,47)],
      "| GA =", [json.load(open(f'{BASE}/pilot/ga_excl/seed{s}/best_of_run.json'))['realized_unique_evals'] for s in (11,23,47)],
      "| GA_wrong =", [json.load(open(f'{BASE}/pilot/ga_wrong/seed{s}/best_of_run.json'))['realized_unique_evals'] for s in (11,23,47)],
      "| hardened =", [json.load(open(f'{BASE}/hardened/ga_excl_hardened/seed{s}/best_of_run.json'))['realized_unique_evals'] for s in (11,23,47)],
      "| 7b =", [json.load(open(f'{BASE}/target_qwen2.5_7b/ga_excl/seed{s}/best_of_run.json'))['realized_unique_evals'] for s in (11,23,47)])
print("Q3 residual artefact per hardened seed:", json.dumps(resid))
print("GA gen0->gen1 (fit0, fit1, cov0, cov1) per seed:", {s: [round(x,3) for x in v] for s, v in ga_gen1.items()})
print("OPRO corrected best-of-step coverage trajectories:",
      {s: [round(c,3) for c in trajs['opro_excl'][s][1]] for s in (11,23,47)})
print("Rescoring detail:", json.dumps(rescore))
print("Anatomy:", json.dumps(anat))
print("Landscape bins OPRO (hi,mid,lo):", [round(x,3) for x in ob], " GA:", [round(x,3) for x in bin_means(ga_u)])
print("Central rows:", json.dumps(central_rows))

# figure data dump
fig_data = {
    "fig1": {
        "opro": [{"cov": l["coverage"], "fit": l["fitness"]} for l in opro_u],
        "ga": [{"cov": l["coverage"], "fit": l["fitness"]} for l in ga_u],
        "baseline_dev": {"cov": 1.0, "fit": BASE_DEV},
        "opro_bins": {"hi": ob[0], "mid": ob[1], "lo": ob[2]},
    },
    "fig2": {reg: {s: {"gens": trajs[reg][s][0], "cov": trajs[reg][s][1]} for s in (11, 23, 47)}
             for reg in ("ga_excl", "ga_wrong", "hardened")},
    "fig3": central_rows,
    "fig4": json.load(open(f"{BASE}/battery/summary.json")),
    "fig5": {
        f"{arm}/{seed}": {
            "reported": best_runs[(arm, seed)]["test"]["f1_used_strict"],
            "f_wrong": best_runs[(arm, seed)]["test"]["f1_wrong_strict"],
            "forced": mech[f"{arm}_seed{seed}_KISITLI"]["f1_used"],
            "coverage": best_runs[(arm, seed)]["test"]["coverage_strict"],
        } for (arm, seed) in [("opro_excl", 11), ("opro_excl", 23), ("opro_excl", 47),
                              ("ga_excl", 11), ("ga_excl", 23), ("ga_excl", 47)]
    },
    "fig5_real_loose256": {"ga_excl/11": central["ga_excl_seed11"]["real_f1_loose256"],
                           "opro_excl/47": central["opro_excl_seed47"]["real_f1_loose256"]},
    "resid": resid, "rescore": rescore,
}
json.dump(fig_data, open(f"{OUT}/figure_data.json", "w"), indent=1)
json.dump([{"section": s, "name": n, "expected": e, "got": g, "pass": ok} for s, n, e, g, ok in report],
          open(f"{OUT}/verification.json", "w"), indent=1)
print("\nWrote", f"{OUT}/figure_data.json", "and verification.json")
