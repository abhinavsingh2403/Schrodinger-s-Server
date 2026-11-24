"""Evaluate the first recorded S3 prefix per session in independent labelled captures."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from analysis.exp0_permutation_null import permute
from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from analysis.null_diagnosis import SEED
from analysis.null_root_cause import dot, normalize
from analysis.posthoc_ml_eval import optimize
from gatekeeper.features import EVENT_COUNTERS, stage_counters, stage_vector


def prefixes(rows):
    counts = defaultdict(Counter)
    seq = Counter()
    samples = {}
    for row in rows:
        key = row["session"]
        if "event" in row:
            seq[key] += 1
            if seq[key] != row["seq"]:
                raise ValueError("Incomplete event sequence")
            field = EVENT_COUNTERS.get(row["event"])
            if field:
                counts[key][field] += 1
        elif row["stage"] == "S3":
            if row["last_seq"] != seq[key] or not seq[key]:
                raise ValueError("Invalid S3 boundary")
            expected = stage_counters("S3",counts[key])
            if any(row["features"].get(k) != v for k,v in expected.items()):
                raise ValueError("Snapshot mismatch")
            label = row["label"]
            if label not in (0,1):
                raise ValueError("Expected binary label")
            samples.setdefault(key,(stage_vector("S3",expected),label))
    return samples


def load(path):
    with path.open() as f:
        return prefixes(json.loads(line) for line in f)


def evaluate(train,test):
    if train.keys() & test.keys():
        raise ValueError("Session appears in both partitions")
    x,y = zip(*train.values())
    xt,yt = zip(*test.values())
    if set(y) != {0,1} or set(yt) != {0,1}:
        raise ValueError("Both labels required in each partition")
    model = PurePythonLogisticRegression(C=.01)
    # Bound the step by the L2 curvature 1/(C*n) on this tiny training sample.
    model.lr = min(model.lr, model.C*len(x)/2)
    model.mins = list(map(min,zip(*x)))
    model.ranges = [max(1e-6,max(col)-lo) for col,lo in zip(zip(*x),model.mins)]
    a = [normalize(r,model) for r in x]
    t = [normalize(r,model) for r in xt]
    results = {}
    for name,labels in (("Real",y),("Constant",[sum(y)/len(y)]*len(y)),("Shuffle",permute(list(y),SEED))):
        _,_,weights,bias = list(optimize(a,labels,model))[-1]
        results[name] = recall_at_budget([bias+dot(weights,r) for r in t],list(yt),.1)
    results["Negative activity"] = recall_at_budget([-sum(r) for r in t],list(yt),.1)
    results["Random"] = recall_at_budget([0.]*len(t),list(yt),.1)
    return results


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("train","test","output"):
        parser.add_argument("--"+arg,type=Path,required=True)
    parser.add_argument("--human-study",action="store_true")
    args = parser.parse_args()
    train,test = load(args.train),load(args.test)
    results = evaluate(train,test)
    valid = abs(results["Shuffle"]-results["Random"]) <= .02
    scope = "Human-provided outcomes (exploratory)." if args.human_study else "SYNTHETIC harness data. Label = script type. Mechanism check only, tiny N."
    lines = ["# S3 prefix evaluation","",scope,"",f"Train sessions {len(train)}, test sessions {len(test)}. First S3 per session, 10% budget, expected cutoff ties.",
             "Balanced optimizer uses the archived C and caps its step at C*n/2 for small samples.",
             "", "| Scorer | Recall |","|---|---:|"]
    lines.extend(f"| {name} | {r:.6f} |" for name,r in results.items())
    lines.append("Shuffle diagnostic: "+("within random +/-0.02." if valid else "INVALID (outside random +/-0.02)."))
    lines.append("Exploratory only. No inference about real attackers or validated ML.")
    args.output.write_text("\n".join(lines)+"\n")
