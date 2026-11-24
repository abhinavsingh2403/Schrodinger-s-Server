# Balanced fallback sensitivity

Post-hoc exploratory, not part of the pre-registered gate.

The fallback ignores grid.json class_weight=balanced. Minimal fix: weight each binary training example by n/(2*n_class) in both loss gradients. Fixed C=0.01, steps=60, lr=0.5, training sample and test cohort held fixed. Test recall at 10%: unweighted 0.291966, balanced 0.294629. Balanced intercept -0.8597171; slopes in archived feature order: 0, -0.6578962, -0.2511736, -0.001329956, -0.07160136, 2.990761, 0.001440297, 0, 0.0890835. This isolates weighting; it does not reproduce the grid's optimizer or rerun model selection. The exact constant-target solution ranks all sessions equally (recall 0.100007). Aggregate timing and source concentration remain limitations. No gate revision or validated ML claim.
