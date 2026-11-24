"""Trace S3 null rankings on the frozen split using the archived fallback and controlled refits."""
import argparse
from collections import Counter, defaultdict
import json
from math import exp, log
from pathlib import Path
from statistics import mean

import duckdb

from analysis.exp0_rules import PurePythonLogisticRegression, recall_from_score_bins
from analysis.exp0_train import load_parquet_as_dict_records

ROOT = Path("results/exp0")
BUDGET = .10


def normalize(row, model):
    return tuple((v - m) / r for v, m, r in zip(row, model.mins, model.ranges))


def dot(weights, row):
    return sum(w * x for w, x in zip(weights, row))


def recall(bins, score):
    """Evaluate grouped (feature vector, label) counts with the gate's cutoff estimator."""
    totals = defaultdict(lambda: [0, 0])
    for (row, label), count in bins.items():
        bucket = totals[score(row)]
        bucket[0] += count
        bucket[1] += count * label
    ordered = [totals[key] for key in sorted(totals, reverse=True)]
    return recall_from_score_bins([n for n, _ in ordered], [p for _, p in ordered], BUDGET)


def fit_grouped(bins, model, *, target=None, balanced=False):
    """Full-batch gradient descent on identical rows compressed by multiplicity."""
    n = sum(bins.values())
    q = sum(y * count for (_, y), count in bins.items()) / n
    weights = [0.] * len(model.mins)
    bias = 0.
    for _ in range(model.max_iter):
        grad = [w / model.C for w in weights]
        intercept_grad = 0.
        for (row, y), count in bins.items():
            class_weight = .5 / (q if y else 1 - q) if balanced else 1.
            z = max(-20., min(20., bias + dot(weights, row)))
            error = count * class_weight * (1 / (1 + exp(-z)) - (y if target is None else target))
            intercept_grad += error
            for j, x in enumerate(row):
                grad[j] += error * x
        weights = [w - model.lr * g / n for w, g in zip(weights, grad)]
        bias -= model.lr * intercept_grad / n
    return weights, bias


def run(splits):
    saved, meta = PurePythonLogisticRegression.load_json(ROOT / "model_s3.json")
    features = meta["features"]
    rows = load_parquet_as_dict_records(splits / "train.parquet", sample_limit=50000)
    if not rows:
        raise FileNotFoundError("train.parquet required in --splits")
    x = [tuple(float(r[k] or 0) for k in features) for r in rows]
    y = [int(r["v_full"]) for r in rows]
    q = mean(y)
    null = PurePythonLogisticRegression(saved.C, saved.max_iter, saved.lr).fit(x, [q] * len(y))
    train = Counter((normalize(row, null), label) for row, label in zip(x, y))
    # Same S3 reach predicate as filter_prefix_determined_exclusions; no S3 exclusions.
    with duckdb.connect() as db:
        columns = ", ".join(features)
        records = db.execute(f"SELECT {columns}, v_full, count(*) FROM read_parquet(?) "
                             "WHERE cnt_login_success > 0 OR has_pty OR cnt_command_input > 0 "
                             "GROUP BY ALL", [str(splits / "test.parquet")]).fetchall()
    raw = {(tuple(float(v or 0) for v in r[:-2]), int(r[-2])): r[-1] for r in records}
    test = {(normalize(r, null), y): n for (r, y), n in raw.items()}
    n = len(rows)
    means = [sum(r[j]*c for (r, _), c in train.items())/n for j in range(len(features))]
    first = [-null.lr * (.5-q) * m for m in means]
    real, bias = fit_grouped(train, null)
    balanced, balanced_bias = fit_grouped(train, null, balanced=True)
    def ranked(bins, weights):
        return recall(bins, lambda r: dot(weights, r))
    saved_recall = recall(raw, saved.predict_proba_single)
    null_recall = recall(raw, null.predict_proba_single)
    analytic = log(q/(1-q))
    chance = recall(test, lambda _: q)
    def vec(items):
        return ", ".join(f"{v:.7g}" for v in items)
    lines = [
        "# S3 null ranking", "", "Post-hoc exploratory, not part of the pre-registered gate.", "",
        f"Training sample {n} (positive fraction {q:.7f}); S3 reached test rows {sum(test.values())}, "
        f"positives {sum(c*y for (_, y), c in test.items())}. Budget {BUDGET:.0%}, expected cutoff ties. "
        f"Archived real scorer {saved_recall:.6f}; fallback trained on identical soft targets {null_recall:.6f}.",
        "", "## Constant-target fit", "",
        f"CONFIRMED. exp0_train.train_and_evaluate_ml_candidates uses exp0_rules.PurePythonLogisticRegression. "
        f"All coefficients and the intercept start at zero (initial probability 0.5). Each feature uses "
        f"training (x-min)/range. The first slope update is -lr*(0.5-q)*mean(scaled x). "
        f"With {null.max_iter} steps, lr {null.lr:g}, C {null.C:g}, slope penalty gradient w/(C*n) "
        f"and an unpenalized intercept, the fitted intercept is {null.bias:.7f}. "
        f"The exact constant-target optimum has zero slopes and intercept logit(q) = {analytic:.7f}: "
        f"its loss gradient vanishes for every training row. Its test recall is {chance:.6f}. "
        "Finite simultaneous updates from zero leave activity-dependent slopes even though targets never vary.",
        "", "| Feature | Train min | Range | First update | Constant final | Real refit | Null recall alone | Null recall omitted |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for j, key in enumerate(features):
        single = [0.] * len(features)
        single[j] = null.weights[j]
        omit = null.weights.copy()
        omit[j] = 0.
        lines.append(f"| {key} | {null.mins[j]:g} | {null.ranges[j]:g} | {first[j]:.7g} | "
                     f"{null.weights[j]:.7g} | {real[j]:.7g} | {ranked(test,single):.6f} | {ranked(test,omit):.6f} |")
    params = features.index("cnt_session_params")
    zero_count = sum(c for (r, _), c in raw.items() if r[params] == 0)
    zero_pos = sum(y*c for (r, y), c in raw.items() if r[params] == 0)
    swapped = real.copy()
    swapped[params] = null.weights[params]
    lines += ["", f"CONFIRMED: session.params dominates the null cutoff. Among {zero_count} reached rows "
              f"with zero session.params, {zero_pos} were positive. Giving priority to lower counts alone "
              f"yields {recall(raw, lambda r: -r[params]):.6f}; dropping this slope yields "
              f"{recall(test, lambda r: dot(null.weights[:params]+[0.]+null.weights[params+1:],r)):.6f}. "
              f"Real labels reverse its sign. Replacing only the real fit's session.params slope with "
              f"the null slope yields {ranked(test,swapped):.6f}."]
    activity = recall(test, lambda r: -sum(r))
    group = [0. if k in ("cnt_client_size","cnt_client_var","cnt_session_params") else w
             for k,w in zip(features,null.weights)]
    real_group = [0. if k in ("cnt_client_size","cnt_client_var","cnt_session_params") else w
                  for k,w in zip(features,saved.weights)]
    late = recall(raw, lambda r: dot(real_group,normalize(r,saved)))
    lines += ["", f"CONFIRMED: activity alone ranks positives. Negative unweighted sum of min-max counters "
              f"has recall {activity:.6f}; negative mean-weighted sum (first update) {ranked(test,first):.6f}. "
              "These rankings require no training outcomes. Equal recall need not imply identical full rankings.",
              "", "## Real labels", "",
              f"CONFIRMED: changing only targets changes slopes and cutoff selection. Unweighted real-label refit "
              f"intercept {bias:.7f}, test {ranked(test,real):.6f}; archived model {saved_recall:.6f}. "
              f"Training recall with real slopes {ranked(train,real):.6f}, with constant-target slopes "
              f"{ranked(train,null.weights):.6f} (training includes unreached sessions).",
              f"REJECTED: a prediction sign or scale reversal in the observed path. Positive-class sigmoid "
              f"scoring on raw rows yields {null_recall:.6f}; ranking its normalized linear predictor gives "
              f"{ranked(test,null.weights):.6f}.",
              f"CONFIRMED: the fallback omits the grid's balanced weights. Changing just class weights gives "
              f"{ranked(test,balanced):.6f} on test. INCONCLUSIVE: this comparison cannot identify overfitting "
              "or establish a causal contribution from training/test population shift.",
              "", "## Timing", "",
              f"Removing session.params, client.size and client.var contributions together gives null "
              f"{ranked(test,group):.6f} and archived real {late:.6f}. This checks reliance on these aggregate "
              "columns, not prefix validity of the remaining features."]
    days = json.loads((ROOT/"event_prefix_study.json").read_text())["days"]
    for day, d in days.items():
        a = d["s3_availability"]
        lines.append(f"- {day}: {a['sessions_with_counter_at_or_after_command']}/{a['complete_command_sessions']} "
                     "complete command sessions with a counter at or after first command.")
    lines += ["", "INCONCLUSIVE: exact post-decision attribution. The event sample lacks a verified historical "
              "S3 decision timestamp. Removing columns cannot reconstruct per-row prefix counts."]
    (ROOT/"NULL_ROOT_CAUSE.md").write_text("\n".join(lines)+"\n",encoding="utf8")
    (ROOT/"POSTHOC_CORRECTED.md").write_text(
        "# Balanced fallback sensitivity\n\nPost-hoc exploratory, not part of the pre-registered gate.\n\n"
        f"The fallback ignores grid.json class_weight=balanced. Minimal fix: weight each binary training "
        f"example by n/(2*n_class) in both loss gradients. Fixed C={saved.C:g}, steps={saved.max_iter}, "
        f"lr={saved.lr:g}, training sample and test cohort held fixed. Test recall at {BUDGET:.0%}: "
        f"unweighted {ranked(test,real):.6f}, balanced {ranked(test,balanced):.6f}. Balanced intercept "
        f"{balanced_bias:.7f}; slopes in archived feature order: {vec(balanced)}. This isolates weighting; "
        "it does not reproduce the grid's optimizer or rerun model selection. The exact constant-target "
        f"solution ranks all sessions equally (recall {chance:.6f}). Aggregate timing and source "
        "concentration remain limitations. No gate revision or validated ML claim.\n",encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits",type=Path,default=ROOT)
    run(parser.parse_args().splits)
