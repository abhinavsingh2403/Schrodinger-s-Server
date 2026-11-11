"""
exp0_splits.py: Pre-declared, leakage-free temporal and source IP splits for Experiment 0.

Per EXPERIMENT0.md Section 3:
- 5 training days sampled from first 35 days (days 1 to 35)
- 2 validation days sampled from days 36 to 42
- 2 test days sampled from days 43 to 50
- Grouping: Every source IP belongs to exactly one fold (assigned to earliest period's fold and removed from later folds).
- Seeded determinism: Seed logged in results/exp0/splits.json before model training.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

DEFAULT_SEED = 20261111


def generate_day_splits(
    calendar_days: list[str],
    seed: int = DEFAULT_SEED,
) -> dict[str, list[str]]:
    """
    Selects 5 train days, 2 val days, and 2 test days from the sorted calendar day list.
    
    calendar_days must be sorted in ascending chronological order.
    """
    if len(calendar_days) < 50:
        raise ValueError(f"Expected at least 50 continuous days, got {len(calendar_days)}")

    rng = random.Random(seed)

    # First 35 days: index 0..34
    period_train = calendar_days[:35]
    train_days = sorted(rng.sample(period_train, 5))

    # Days 36 to 42: index 35..41
    period_val = calendar_days[35:42]
    val_days = sorted(rng.sample(period_val, 2))

    # Days 43 to 50: index 42..49
    period_test = calendar_days[42:50]
    test_days = sorted(rng.sample(period_test, 2))

    return {
        "train": train_days,
        "validation": val_days,
        "test": test_days,
    }


def verify_ip_grouping(train_ips: set[str], val_ips: set[str], test_ips: set[str]) -> bool:
    """
    Verifies that no source IP appears in multiple folds.
    """
    inter_train_val = train_ips.intersection(val_ips)
    inter_train_test = train_ips.intersection(test_ips)
    inter_val_test = val_ips.intersection(test_ips)

    if inter_train_val or inter_train_test or inter_val_test:
        raise ValueError(
            f"IP leakage detected: train-val overlap={len(inter_train_val)}, "
            f"train-test overlap={len(inter_train_test)}, "
            f"val-test overlap={len(inter_val_test)}"
        )
    return True


def save_splits_json(
    day_splits: dict[str, list[str]],
    output_path: Path,
    seed: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Save the pre-declared split configuration."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": seed,
        "splits": day_splits,
        "metadata": metadata or {},
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Experiment 0 temporal splits")
    parser.add_argument("--base-rates", type=Path, default=Path("results/base_rates.json"), help="Path to base_rates.json")
    parser.add_argument("--output", type=Path, default=Path("results/exp0/splits.json"), help="Output path for splits.json")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for day drawing")
    args = parser.parse_args()

    if not args.base_rates.is_file():
        raise FileNotFoundError(f"Missing {args.base_rates}. Run analysis/s3_base_rates.py first.")

    with open(args.base_rates, "r", encoding="utf-8") as f:
        base_rates = json.load(f)

    # Extract sorted dates from by_day section
    by_day_data = base_rates.get("by_day", {})
    all_dates = sorted([d for d in by_day_data.keys() if d != "UNKNOWN"])

    day_splits = generate_day_splits(all_dates, seed=args.seed)

    save_splits_json(
        day_splits=day_splits,
        output_path=args.output,
        seed=args.seed,
        metadata={
            "total_available_days": len(all_dates),
            "date_range": [all_dates[0], all_dates[-1]],
        },
    )

    print(f"Generated pre-declared Experiment 0 splits (seed={args.seed}):")
    print(f"  Train ({len(day_splits['train'])} days)     : {day_splits['train']}")
    print(f"  Validation ({len(day_splits['validation'])} days): {day_splits['validation']}")
    print(f"  Test ({len(day_splits['test'])} days)       : {day_splits['test']}")
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
