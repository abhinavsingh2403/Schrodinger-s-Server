"""Diagnose S4 ranking equivalence without changing the frozen evaluation."""
import json
from math import ceil
from analysis.experiment1_eval import OUT, FEATURES, load, fit
from analysis.posthoc_ml_eval import optimize, normalize, permute
from analysis.exp0_rules import PurePythonLogisticRegression, metrics_at_budget, train_r7_decision_tree


def ranking(scores):
    """Encode the weak order, preserving score ties."""
    ranks={v:i for i,v in enumerate(sorted(set(scores)))}
    return [ranks[v] for v in scores]


def inclusion(scores, budget=.1):
    """Return each row's expected selection weight under uniform cutoff ties."""
    slots = ceil(len(scores) * budget)
    cutoff = sorted(scores, reverse=True)[slots-1]
    fraction = (slots - sum(s > cutoff for s in scores)) / scores.count(cutoff)
    return [1.0 if s > cutoff else fraction if s == cutoff else 0.0 for s in scores]


def main():
    train,_,test=sorted(OUT.glob('*_S4.parquet'))
    _,y,x=load(train,FEATURES,True)
    _,yt,xt=load(test,FEATURES)
    models={}
    slopes={}
    for name,target in [('real',y),('shuffle',permute(y,42))]:
        model=PurePythonLogisticRegression(C=.01)
        model.mins=list(map(min,zip(*x)))
        model.ranges=[max(1e-6,max(c)-lo) for c,lo in zip(zip(*x),model.mins)]
        step,loss,w,b=list(optimize([normalize(r,model) for r in x],target,model))[-1]
        slopes[name]=dict(weights=dict(zip(FEATURES,w)),intercept=b,steps=step,loss=loss)
        scorer,_=fit(x,target,list(range(len(FEATURES))))
        models[name]=scorer(xt)
    reduced=[i for i,n in enumerate(FEATURES) if n not in ('elapsed','activity','gap')]
    scorer,_=fit(x,y,reduced)
    models['ablation']=scorer(xt)
    tree=train_r7_decision_tree([(r[4],r[3]) for r in x],y)
    models['R7']=tree.predict_proba([(r[4],r[3]) for r in xt])
    for i,name in enumerate(FEATURES):
        for sign in (1,-1):
            models[f'{name}:{sign}']=[sign*r[i] for r in xt]
    models['activity_sum']=[sum(r) for r in xt]
    reference=ranking(models['real'])
    comparisons={k:dict(recall=metrics_at_budget(v,yt,.1)['recall'],
        score_bins=len(set(v)),same_order_as_real=ranking(v)==reference) for k,v in models.items()}
    data=dict(slopes=slopes,comparisons=comparisons,
              ablation_order_equals_R7=ranking(models['ablation'])==ranking(models['R7']))
    pairs = [('real','shuffle'), ('real','activity_sum'), ('ablation','R7')]
    cutoff_lines = []
    for left, right in pairs:
        first, second = inclusion(models[left]), inclusion(models[right])
        changed = sum(a != b for a,b in zip(first,second))
        delta_tp = sum((a-b)*y for a,b,y in zip(first,second,yt))
        cutoff_lines.append(f"{left} versus {right}: {changed} of {len(yt)} selection weights differ "
                            f"at the cutoff; expected true-positive difference {delta_tp:.8g}.")
    data['cutoff_comparisons'] = cutoff_lines
    (OUT/'root_cause_details.json').write_text(json.dumps(data,indent=2)+'\n')
    matches=[k for k,v in comparisons.items() if k not in ('real','shuffle','ablation','R7') and v['same_order_as_real']]
    lines=['# S4 root-cause diagnosis','Post-hoc exploratory, outside the pre-registered protocol.',
        f"Identical fitted slopes: {'CONFIRMED' if slopes['real']['weights']==slopes['shuffle']['weights'] else 'REJECTED'}.",
        f"Identical real/shuffle weak order: {comparisons['shuffle']['same_order_as_real']}.",
        f"Label-free exact ranking reproduction: {'CONFIRMED' if matches else 'INCONCLUSIVE'}; matching rankers {matches}.",
        f"Ablation/R7 identical weak order: {'CONFIRMED' if data['ablation_order_equals_R7'] else 'REJECTED'}.",
        f"Label-free feature sum reproduces recall: {'CONFIRMED' if comparisons['activity_sum']['recall']==comparisons['real']['recall'] else 'REJECTED'}.",
        "Elapsed time alone comes close. Both fits give positive weight to elapsed time, activity and auth counts. "
        "Removing elapsed time, activity and gap leaves auth counts to distinguish rows; R7 also uses auth counts.",
        *cutoff_lines, '', '| Ranker | Recall at 10% | Score bins | Same weak order as real |','|---|---:|---:|---|']
    lines += [f"| {k} | {v['recall']} | {v['score_bins']} | {v['same_order_as_real']} |" for k,v in comparisons.items()]
    lines+=['','Exact weights and loss are in root_cause_details.json. Equal recall alone cannot establish equal rankings. This diagnostic reuses the exposed test cohort and supplies no fresh validation.',
            'Reproduce with `python -m analysis.experiment1_root_cause`.']
    (OUT/'ROOT_CAUSE.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    main()
