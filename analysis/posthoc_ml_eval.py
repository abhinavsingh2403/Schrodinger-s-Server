"""Post-hoc balanced S3 fits on frozen data, with identical controls and cutoff ties."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import duckdb

from analysis.exp0_permutation_null import permute
from analysis.exp0_rules import metrics_at_budget, pr_auc_score, PurePythonLogisticRegression
from analysis.exp0_train import filter_prefix_determined_exclusions, load_parquet_as_dict_records
from analysis.null_root_cause import ROOT, normalize, dot
from analysis.null_diagnosis import SEED
from gatekeeper.features import stage_vector

TOL = 1e-8
CHECKPOINTS = (60, 200, 500, 1000)
VOLUME = {"cnt_session_params", "cnt_client_size", "cnt_client_var"}


def columns(names, reduced):
    return [i for i, name in enumerate(names) if not reduced or name not in VOLUME]


def balanced_mass(n, positives):
    """Weights of negative and positive outcomes, including fractional targets."""
    return n / (2 * (n - positives)), n / (2 * positives)


def optimize(x, labels, model, checkpoints=CHECKPOINTS, tol=TOL, limit=50000):
    n = len(x)
    neg, pos = balanced_mass(n, sum(labels))
    groups = {}
    for (row, y), count in Counter(zip(x, labels)).items():
        mass, target = groups.get(row, (0., 0.))
        groups[row] = mass + count*((1-y)*neg + y*pos), target + count*y*pos
    if min(labels) == max(labels):
        # Balanced fractional targets contribute exactly equal positive and negative mass.
        groups = {row: (mass, mass/2) for row, (mass, _) in groups.items()}
    w = [0.] * len(x[0])
    bias = 0.
    previous = math.inf
    for step in range(limit+1):
        grad = [v / model.C for v in w]
        gb = 0.
        loss = dot(w,w)/(2*model.C)
        for row, (mass,target) in groups.items():
            z = bias + dot(w,row)
            loss += mass*math.log1p(math.exp(z))-target*z
            err = mass/(1+math.exp(-z))-target
            gb += err
            for j,v in enumerate(row):
                grad[j] += err*v
        loss /= n
        stopped = step >= max(checkpoints) and abs(previous-loss) < tol
        if step in checkpoints or stopped:
            yield step, loss, tuple(w), bias
        if stopped:
            return
        previous = loss
        w = [v-model.lr*g/n for v,g in zip(w,grad)]
        bias -= model.lr*gb/n
    raise RuntimeError("Loss did not converge")


def evaluate(splits):
    model, meta = PurePythonLogisticRegression.load_json(ROOT/"model_s3.json")
    names = meta["features"]
    train = load_parquet_as_dict_records(splits/"train.parquet",sample_limit=50000)
    # Push the reach predicate into parquet reading to bound memory.
    with duckdb.connect() as db:
        cur = db.execute("select * from read_parquet(?) where cnt_login_success>0 or has_pty or cnt_command_input>0",
                         [str(splits/"test.parquet")])
        keys = [d[0] for d in cur.description]
        test,_ = filter_prefix_determined_exclusions([dict(zip(keys,r)) for r in cur.fetchall()],"S3")
    labels = [int(r["v_full"]) for r in train]
    yt = [int(r["v_full"]) for r in test]
    raw = [stage_vector("S3",r) for r in train]
    model.mins = list(map(min,zip(*raw)))
    model.ranges = [max(1e-6,max(col)-lo) for col,lo in zip(zip(*raw),model.mins)]
    x = [normalize(r,model) for r in raw]
    xt = [normalize(stage_vector("S3",r),model) for r in test]
    def metrics(scores):
        m = metrics_at_budget(scores,yt,.1)
        return m["recall"],m["precision"],pr_auc_score(scores,yt)
    lines = ["# Corrected S3 evaluation","","Post-hoc exploratory, not part of the pre-registered gate.","",
             f"Frozen train sample {len(x)}, reached test {len(xt)}, positives {sum(yt)}. C={model.C}, lr={model.lr}. "
             f"Balanced positive/negative loss terms include fractional constant targets. Stop after the last checkpoint "
             f"when consecutive penalized mean losses differ by less than {TOL:g}. "
             "Exploratory shuffle acceptance interval fixed at random recall ±0.02. One seed is a diagnostic only.",
             "", "| Baseline | Recall | Precision | PR-AUC |","|---|---:|---:|---:|"]
    def fmt(values):
        return " | ".join(f"{v:.6f}" for v in values)
    chance = metrics([0.]*len(xt))
    activity = metrics([-sum(r) for r in xt])
    methods = json.loads((ROOT/"evaluation_metrics.json").read_text())["methods"]
    rule = methods["R7_decision_tree"]
    b = rule["budgets"]["10%"]
    for name,m in [("Random (expected ties)",chance),("Negative activity",activity),
                   ("R7 (archived fitted rule)",(b["recall"],b["precision"],rule["pr_auc"]))]:
        lines.append(f"| {name} | {fmt(m)} |")
    lines += ["","R7 is reported separately because training uses labels. All comparisons use the full negative-activity baseline.",
              "", "| Columns | Target | Step | Loss | Recall | Precision | PR-AUC |","|---|---|---:|---:|---:|---:|---:|"]
    verdicts, strata = [], []
    sources = {src: i for i,src in enumerate(sorted({r["src_ip"] for r in test}),1)}
    for reduced,name in [(False,"All"),(True,"Volume removed")]:
        idx = columns(names,reduced)
        def select(rows):
            return [tuple(r[i] for i in idx) for r in rows]
        a,t = select(x),select(xt)
        matched = metrics([-sum(r) for r in t])
        lines.append(f"| {name} | Label-free activity on retained columns | - | - | {fmt(matched)} |")
        recalls = {}
        for kind,y in [("Real",labels),("Constant",[sum(labels)/len(labels)]*len(labels)),
                       ("Shuffle",permute(labels,SEED))]:
            fits = list(optimize(a,y,model))
            for step,loss,w,bias in (fits if kind=="Real" and not reduced else fits[-1:]):
                scores = [bias+dot(w,r) for r in t]
                m = metrics(scores)
                lines.append(f"| {name} | {kind} | {step} | {loss:.10f} | {fmt(m)} |")
            recalls[kind] = m[0]
            if kind=="Real":
                cut = sorted(scores,reverse=True)[math.ceil(.1*len(t))-1]
                share = (math.ceil(.1*len(t))-sum(v>cut for v in scores))/scores.count(cut)
                groups = {}
                for r,y,v in zip(test,yt,scores):
                    if y:
                        for key in (str(r["day"]), f"{r['day']} / source {sources[r['src_ip']]}", "transfer" if r["cnt_file_upload"] or r["cnt_file_download"] else "other"):
                            hits,npos = groups.get(key,(0.,0))
                            groups[key] = hits+(1 if v>cut else share if v==cut else 0),npos+1
                for key,(hits,npos) in sorted(groups.items()):
                    strata.append(f"| {name} | {key} | {npos} | {hits/npos:.6f} |")
        valid = abs(recalls["Shuffle"]-chance[0]) <= .02
        verdict = "INCONCLUSIVE (INVALID shuffle)" if not valid else ("REJECTED" if recalls["Real"] <= activity[0] else "INCONCLUSIVE (point estimate only)")
        verdicts.append(f"| {name} | {recalls['Real']:.6f} | {recalls['Shuffle']:.6f} | {verdict} |")
    lines += ["",f"Shuffle seed {SEED}. INVALID means label permutation still ranked positives outside the declared interval.",
              "", "| Features | Real recall | Shuffle recall | Beats best label-free baseline? |","|---|---:|---:|---|",
              *verdicts,"| Verified pre-command | — | — | INCONCLUSIVE |","",
              "Pre-command fit and controls NOT RUN. The timing audit cannot certify a complete feature set at the decision boundary. "
              "After establishing a verified feature list, add it to the ladder and rerun the command below.",
              "", "| Features | Test day or positive subtype | Positives | Recall at global cutoff |","|---|---|---:|---:|",*strata,
              "", "Reproduce with frozen parquets: `python -m analysis.posthoc_ml_eval --splits results/exp0`."]
    (ROOT/"POSTHOC_ML_EVAL.md").write_text("\n".join(lines)+"\n",encoding="utf8")


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits",type=Path,default=ROOT)
    evaluate(parser.parse_args().splits)
