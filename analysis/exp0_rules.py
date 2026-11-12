"""
exp0_rules.py: Pre-declared simple-rule baselines (R0 to R7) for Experiment 0.

Per EXPERIMENT0.md Section 7:
- R0: Random score (uniform [0, 1])
- R1: 1 if login succeeded, else 0 (S2+)
- R2: 1 if PTY / terminal requested (S3+)
- R3: 1 if interactive shell rather than exec (S3+)
- R4: Delay / duration score (S4+)
- R5: Rarity score (negative log frequency of version/sensor features) (S1+)
- R6: Number of failed logins before success (S2+)
- R7: Depth-3 decision tree on simple features R1-R6 (S2+)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
from typing import Any


def score_r0_random(n: int, seed: int = 42) -> list[float]:
    """R0: Uniform random baseline."""
    rng = random.Random(seed)
    return [rng.random() for _ in range(n)]


def score_r1_login_success(cnt_login_success: list[int]) -> list[float]:
    """R1: 1 if login succeeded, else 0."""
    return [1.0 if x > 0 else 0.0 for x in cnt_login_success]


def score_r2_pty_requested(has_pty: list[bool]) -> list[float]:
    """R2: 1 if PTY requested, else 0."""
    return [1.0 if p else 0.0 for p in has_pty]


def score_r3_interactive(is_interactive: list[bool]) -> list[float]:
    """R3: 1 if the session is an interactive shell rather than a single exec command, else 0.

    Per EXPERIMENT0.md Section 7: Valid from S3. If undistinguishable, drop R3.
    In Cowrie event logs, interactive sessions request a pty or open a shell channel.
    """
    return [1.0 if x else 0.0 for x in is_interactive]


def score_r4_timing_delay(delay_seconds: list[float], sign: int = 1) -> list[float]:
    """R4: Seconds from login success to first command.

    Per EXPERIMENT0.md Section 7: Valid from S4.
    Direction (sign) is selected on training data.
    """
    return [float(sign * max(0.0, d)) for d in delay_seconds]


def score_r5_rarity(items: list[str], train_counts: dict[str, int], total_train: int) -> list[float]:
    """R5: Negative log frequency of item in training set (rarity)."""
    scores = []
    for item in items:
        count = train_counts.get(item, 1)  # Laplace add-1 smoothing
        freq = count / (total_train + len(train_counts))
        scores.append(-math.log(max(freq, 1e-9)))
    return scores


def score_r5b_hassh_rarity(hassh_list: list[str], train_hassh_counts: dict[str, int], total_train: int) -> list[float]:
    """R5b: Negative log frequency of HASSH fingerprint in training set."""
    return score_r5_rarity(hassh_list, train_hassh_counts, total_train)


def score_r6_failed_logins(cnt_login_failed: list[int], sign: int = 1) -> list[float]:
    """R6: Number of failed logins before success."""
    return [float(sign * x) for x in cnt_login_failed]


class PurePythonDepth3Tree:
    """Exact, deterministic depth-3 decision tree classifier for baseline R7.

    Pre-registered in EXPERIMENT0.md §7: Trained exclusively on training data
    using the simple features from R1 to R6.
    """

    def __init__(self, max_depth: int = 3) -> None:
        self.max_depth = max_depth
        self.tree: Any = None

    def fit(self, X: list[list[float]], y: list[int]) -> PurePythonDepth3Tree:
        """Fits binary decision tree maximizing Gini impurity reduction."""
        def gini(labels: list[int]) -> float:
            if not labels:
                return 0.0
            p1 = sum(labels) / len(labels)
            return 2.0 * p1 * (1.0 - p1)

        def build_node(indices: list[int], depth: int) -> dict[str, Any]:
            node_labels = [y[i] for i in indices]
            prob = (sum(node_labels) / len(node_labels)) if node_labels else 0.0
            if depth >= self.max_depth or len(set(node_labels)) <= 1 or len(indices) < 4:
                return {"prob": prob, "leaf": True}

            best_feat = -1
            best_thresh = 0.0
            best_gain = 0.0
            current_gini = gini(node_labels)
            n_samples = len(indices)

            n_features = len(X[0]) if X else 0
            for f_idx in range(n_features):
                vals = sorted(set(X[i][f_idx] for i in indices))
                for v in vals:
                    left = [i for i in indices if X[i][f_idx] <= v]
                    right = [i for i in indices if X[i][f_idx] > v]
                    if not left or not right:
                        continue
                    g_split = (len(left) / n_samples) * gini([y[i] for i in left]) + \
                              (len(right) / n_samples) * gini([y[i] for i in right])
                    gain = current_gini - g_split
                    if gain > best_gain:
                        best_gain = gain
                        best_feat = f_idx
                        best_thresh = v

            if best_gain <= 1e-5:
                return {"prob": prob, "leaf": True}

            left_idx = [i for i in indices if X[i][best_feat] <= best_thresh]
            right_idx = [i for i in indices if X[i][best_feat] > best_thresh]

            return {
                "leaf": False,
                "feature": best_feat,
                "threshold": best_thresh,
                "left": build_node(left_idx, depth + 1),
                "right": build_node(right_idx, depth + 1),
                "prob": prob,
            }

        if X and y:
            self.tree = build_node(list(range(len(y))), depth=0)
        return self

    def predict_proba(self, X: list[list[float]]) -> list[float]:
        """Predicts probability of class 1."""
        def predict_one(x: list[float], node: dict[str, Any]) -> float:
            if node.get("leaf", False):
                return float(node["prob"])
            f = node["feature"]
            t = node["threshold"]
            if x[f] <= t:
                return predict_one(x, node["left"])
            return predict_one(x, node["right"])

        if not self.tree:
            return [0.0 for _ in X]
        return [predict_one(row, self.tree) for row in X]


def train_r7_decision_tree(
    X_train: list[list[float]],
    y_train: list[int],
    max_depth: int = 3,
) -> PurePythonDepth3Tree:
    """Trains R7 depth-3 decision tree on training data only."""
    tree = PurePythonDepth3Tree(max_depth=max_depth)
    tree.fit(X_train, y_train)
    return tree


class PurePythonLogisticRegression:
    """Deterministic pure-Python L2-regularized Logistic Regression classifier.
    
    Provides reliable, zero-dependency candidate modeling when scikit-learn
    is unavailable in the local environment.
    """

    def __init__(self, C: float = 1.0, max_iter: int = 60, lr: float = 0.5) -> None:
        self.C = C
        self.max_iter = max_iter
        self.lr = lr
        self.weights: list[float] = []
        self.bias: float = 0.0
        self.mins: list[float] = []
        self.ranges: list[float] = []

    def fit(self, X: list[list[float]], y: list[int]) -> PurePythonLogisticRegression:
        n_samples = len(X)
        if n_samples == 0:
            return self
        n_features = len(X[0])
        self.weights = [0.0] * n_features
        self.bias = 0.0
        reg = 1.0 / max(1e-9, self.C * n_samples)

        # Robust min-max normalization
        self.mins = [min(row[j] for row in X) for j in range(n_features)]
        self.ranges = [max(1e-6, max(row[j] for row in X) - self.mins[j]) for j in range(n_features)]
        X_norm = [[(row[j] - self.mins[j]) / self.ranges[j] for j in range(n_features)] for row in X]

        for _ in range(self.max_iter):
            grad_w = [0.0] * n_features
            grad_b = 0.0
            for i in range(n_samples):
                z = self.bias + sum(w * x for w, x in zip(self.weights, X_norm[i]))
                z = max(-20.0, min(20.0, z))
                p = 1.0 / (1.0 + math.exp(-z))
                err = p - y[i]
                for j in range(n_features):
                    grad_w[j] += err * X_norm[i][j]
                grad_b += err

            for j in range(n_features):
                self.weights[j] -= self.lr * (grad_w[j] / n_samples + reg * self.weights[j])
            self.bias -= self.lr * (grad_b / n_samples)

        return self

    def predict_proba(self, X: list[list[float]]) -> list[float]:
        if not self.weights or not X:
            return [0.0 for _ in X]
        probs = []
        for row in X:
            x_norm = [(row[j] - self.mins[j]) / self.ranges[j] for j in range(len(self.weights))]
            z = self.bias + sum(w * x for w, x in zip(self.weights, x_norm))
            z = max(-20.0, min(20.0, z))
            p = 1.0 / (1.0 + math.exp(-z))
            probs.append(p)
        return probs

    def predict_proba_single(self, row: list[float]) -> float:
        """Predict P(Y=1) for a single feature vector."""
        if not self.weights or not row:
            return 0.0
        n = min(len(self.weights), len(row))
        x_norm = [(row[j] - self.mins[j]) / self.ranges[j] for j in range(n)]
        z = self.bias + sum(w * x for w, x in zip(self.weights[:n], x_norm))
        z = max(-20.0, min(20.0, z))
        return 1.0 / (1.0 + math.exp(-z))

    def to_dict(self) -> dict[str, Any]:
        """Serialize model weights and normalization parameters to dict."""
        return {
            "model_type": "PurePythonLogisticRegression",
            "C": self.C,
            "max_iter": self.max_iter,
            "lr": self.lr,
            "weights": self.weights,
            "bias": self.bias,
            "mins": self.mins,
            "ranges": self.ranges,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PurePythonLogisticRegression:
        """Deserialize model from dictionary."""
        model = cls(
            C=float(data.get("C", 1.0)),
            max_iter=int(data.get("max_iter", 60)),
            lr=float(data.get("lr", 0.5)),
        )
        model.weights = [float(w) for w in data.get("weights", [])]
        model.bias = float(data.get("bias", 0.0))
        model.mins = [float(m) for m in data.get("mins", [])]
        model.ranges = [float(r) for r in data.get("ranges", [])]
        return model

    def save_json(self, path: Path | str, metadata: dict[str, Any] | None = None) -> None:
        """Save model state and optional metadata to JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        if metadata:
            payload.update(metadata)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    @classmethod
    def load_json(cls, path: Path | str) -> tuple[PurePythonLogisticRegression, dict[str, Any]]:
        """Load model state and metadata from JSON file."""
        p = Path(path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        model = cls.from_dict(data)
        return model, data


def recall_at_budget(scores: list[float], labels: list[int], budget: float, seed: int = 42) -> float:
    """
    Computes recall of value=1 sessions within the top `budget` fraction of highest-scored sessions.
    
    Ties broken at random with a fixed seed per EXPERIMENT0.md §7.
    budget is in (0, 1], e.g. 0.10 for 10% budget.
    """
    if not scores or not labels or len(scores) != len(labels):
        raise ValueError("Scores and labels must be non-empty and of equal length.")

    total_positives = sum(labels)
    if total_positives == 0:
        return 0.0

    n = len(scores)
    k = max(1, int(math.ceil(budget * n)))

    # Deterministic tie-breaking using fixed seed RNG per EXPERIMENT0.md §7
    rng = random.Random(seed)
    tie_breakers = [rng.random() for _ in range(n)]

    # Sort descending by primary score, tie-broken by secondary random float
    indices = list(range(n))
    indices.sort(key=lambda i: (scores[i], tie_breakers[i]), reverse=True)

    top_k_indices = indices[:k]
    positives_captured = sum(labels[i] for i in top_k_indices)
    return positives_captured / total_positives
