"""Evaluate the frozen day splits with a validation-selected baseline and paired intervals."""
import json
from pathlib import Path

import duckdb

from analysis.experiment1_dataset import FEATURES
from analysis.exp0_rules import PurePythonLogisticRegression, metrics_at_budget, pr_auc_score, train_r7_decision_tree
from analysis.exp0_train import paired_cluster_bootstrap_delta
from analysis.posthoc_ml_eval import dot, normalize, optimize, permute

OUT=Path("results/exp1")


def load(path, names, limit=False):
    with duckdb.connect() as db:
        rows=db.execute("select source,label,"+",".join(names)+" from read_parquet(?) order by key"+
                        (" limit 10000" if limit else ""),[str(path)]).fetchall()
    return [r[0] for r in rows],[int(r[1]) for r in rows],[r[2:] for r in rows]


def fit(x,y,indices):
    model=PurePythonLogisticRegression(C=.01)
    cols=[tuple(row[i] for i in indices) for row in x]
    model.mins=list(map(min,zip(*cols)))
    model.ranges=[max(1e-6,max(col)-lo) for col,lo in zip(zip(*cols),model.mins)]
    step,loss,w,b=list(optimize([normalize(row,model) for row in cols],y,model))[-1]
    def score(rows):
        cache={row:b+dot(w,normalize(tuple(row[i] for i in indices),model)) for row in set(rows)}
        return [cache[row] for row in rows]
    return score,dict(steps=step,loss=loss)


def verdict(shuffle,positive,delta,lower):
    if abs(shuffle-.1)>.0200000001:
        return "INVALID"
    if positive<500:
        return "INCONCLUSIVE"
    return "CONFIRMED" if delta>=.05 and lower>0 else "REJECTED"


def evaluate(stage):
    train,val,test=sorted(OUT.glob('*_'+stage+'.parquet'))
    names=FEATURES[:6] if stage=='S2' else FEATURES
    _,y,x=load(train,names,True)
    _,yv,xv=load(val,names)
    def rules(rows):
        return [(r[4],r[3]) for r in rows]
    tree=train_r7_decision_tree(rules(x),y)
    def baselines(rows):
        return dict(random=[0]*len(rows),activity=[r[1] for r in rows],
                    negative_activity=[-r[1] for r in rows],R7=tree.predict_proba(rules(rows)))
    validation={k:metrics_at_budget(scores,yv,.1)['recall'] for k,scores in baselines(xv).items()}
    best=max(validation,key=validation.get)
    full=list(range(len(names)))
    ablated=[i for i,n in enumerate(names) if n not in ('elapsed','activity','gap')]
    scorers={}
    fits={}
    for k,target,cols in [('learned',y,full),('shuffle',permute(y,42),full),
                          ('constant',[sum(y)/len(y)]*len(y),full),('ablation',y,ablated)]:
        scorers[k],fits[k]=fit(x,target,cols)
    sources,yt,xt=load(test,names)
    scores=baselines(xt)
    scores.update({k:f(xt) for k,f in scorers.items()})
    metrics={k:dict(pr_auc=pr_auc_score(v,yt),budgets={str(b):metrics_at_budget(v,yt,b)
             for b in (.01,.05,.1,.2)}) for k,v in scores.items()}
    # First appearance in session-key order is independent of the privacy salt.
    ids={s:i for i,s in enumerate(dict.fromkeys(sources))}
    delta,lo,hi=paired_cluster_bootstrap_delta(scores['learned'],scores[best],yt,[ids[s] for s in sources],
        alpha=.05/(3 if stage=='S2' else 2),seed=42)
    status=verdict(metrics['shuffle']['budgets']['0.1']['recall'],sum(yt),delta,lo)
    return dict(day=test.name.split('_')[0],baseline=best,validation=validation,fits=fits,
                metrics=metrics,delta=delta,interval=[lo,hi],verdict=status)


def main():
    rows={stage:evaluate(stage) for stage in ('S2','S4','S5')}
    (OUT/'metrics.json').write_text(json.dumps(rows,indent=2)+'\n')
    lines=['# Experiment 1','Post-hoc relative to Experiment 0. Offline, three audited days, one archive.',
           '', '| Stage | Test day | Best baseline | Learned recall | Baseline recall | Shuffle | Constant | Ablation | Adjusted delta interval | Verdict |',
           '|---|---|---|---:|---:|---:|---:|---:|---|---|']
    for stage,r in rows.items():
        values=[r['metrics'][k]['budgets']['0.1']['recall'] for k in ('learned',r['baseline'],'shuffle','constant','ablation')]
        lines.append('| '+' | '.join(map(str,[stage,r['day'],r['baseline'],*values,r['interval'],r['verdict']]))+' |')
    lines+=['','NO VALIDATED ML GAIN' if all(r['verdict']!='CONFIRMED' for r in rows.values()) else
            'Gain under these controls on these three audited days for '+', '.join(k for k,r in rows.items() if r['verdict']=='CONFIRMED'),
            '', 'Budgets, precision, PR-AUC, convergence and validation selection are in metrics.json. '
            'The table reports recall at the 10% budget. S5 has fewer than 500 test positives.']
    (OUT/'EXPERIMENT1_RESULT.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    main()
