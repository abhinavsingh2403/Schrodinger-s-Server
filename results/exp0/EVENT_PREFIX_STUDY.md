# Three-day event-prefix study (reporting only)

Status: COMPLETE

First listed day of each unchanged official fold, fixed before event outcomes

| Day | Event | Before command | Equal timestamp | After command | Sessions with both |
|---|---|---:|---:|---:|---:|
| 2025-07-07 | cowrie.client.size | 38 | 0 | 18 | 41 |
| 2025-07-07 | cowrie.client.var | 17 | 0 | 0 | 16 |
| 2025-07-07 | cowrie.session.params | 48668 | 0 | 16172 | 48645 |
| 2025-08-03 | cowrie.client.size | 335 | 0 | 21 | 338 |
| 2025-08-03 | cowrie.client.var | 328 | 0 | 0 | 91 |
| 2025-08-03 | cowrie.session.params | 50690 | 0 | 85008 | 50608 |
| 2025-08-09 | cowrie.client.size | 67 | 0 | 33 | 72 |
| 2025-08-09 | cowrie.client.var | 7 | 0 | 0 | 7 |
| 2025-08-09 | cowrie.session.params | 85185 | 0 | 68214 | 85130 |

Whole aggregate S3 vector equals the strictly pre-command vector only when none of its counter events occurs at or after the first command. Missing setup events are reported separately; zero observations do not verify an event ordering guarantee.

| Day | Total sessions | Complete sessions | Complete command sessions | Whole vector strictly before | Counter at/after command | No setup event |
|---|---:|---:|---:|---:|---:|---:|
| 2025-07-07 | 584319 | 579047 | 48645 | 46449 | 2196 | 0 |
| 2025-08-03 | 841952 | 831806 | 50608 | 35371 | 15237 | 0 |
| 2025-08-09 | 825117 | 816671 | 85130 | 72067 | 13063 | 0 |

Primary prefix label: distinct-command count at least the unchanged threshold, or transfer/pivot event (EVAL.md). The input-event-count approximation is reported separately; it is not the primary event-level label.

Diagnostic stage counts:
```json
{
  "2025-07-07": {
    "S3": {
      "reached": 48838,
      "prefix_positive_excluded": 102,
      "eligible": 48736,
      "future_positive": 15915
    },
    "S4": {
      "reached": 48645,
      "prefix_positive_excluded": 102,
      "eligible": 48543,
      "future_positive": 15915
    },
    "S5": {
      "reached": 6214,
      "prefix_positive_excluded": 834,
      "eligible": 5380,
      "future_positive": 5364
    }
  },
  "2025-08-03": {
    "S3": {
      "reached": 50610,
      "prefix_positive_excluded": 97,
      "eligible": 50513,
      "future_positive": 17663
    },
    "S4": {
      "reached": 50608,
      "prefix_positive_excluded": 97,
      "eligible": 50511,
      "future_positive": 17663
    },
    "S5": {
      "reached": 6112,
      "prefix_positive_excluded": 4340,
      "eligible": 1772,
      "future_positive": 1527
    }
  },
  "2025-08-09": {
    "S3": {
      "reached": 85133,
      "prefix_positive_excluded": 93,
      "eligible": 85040,
      "future_positive": 15371
    },
    "S4": {
      "reached": 85130,
      "prefix_positive_excluded": 93,
      "eligible": 85037,
      "future_positive": 15371
    },
    "S5": {
      "reached": 4834,
      "prefix_positive_excluded": 3390,
      "eligible": 1444,
      "future_positive": 1397
    }
  }
}
```

Reporting-only feasibility study; no model performance or new Gate 0 verdict.
S3 anchor is first session.params before first command, a diagnostic proxy requiring runtime mapping review.
Only sessions with connect and close in the same sampled day are included; boundary censoring remains.
Same-timestamp ordering is ambiguous; prefixes conservatively include all events at the anchor timestamp.
No cross-day train/test model is fitted; source-group leakage evaluation remains required before fitting.

Aggregate-approximation comparison:
```json
{
  "2025-07-07": {
    "S3": {
      "reached": 48838,
      "prefix_positive_excluded": 102,
      "eligible": 48736,
      "future_positive": 15915
    },
    "S4": {
      "reached": 48645,
      "prefix_positive_excluded": 102,
      "eligible": 48543,
      "future_positive": 15915
    },
    "S5": {
      "reached": 6214,
      "prefix_positive_excluded": 834,
      "eligible": 5380,
      "future_positive": 5364
    }
  },
  "2025-08-03": {
    "S3": {
      "reached": 50610,
      "prefix_positive_excluded": 97,
      "eligible": 50513,
      "future_positive": 17663
    },
    "S4": {
      "reached": 50608,
      "prefix_positive_excluded": 97,
      "eligible": 50511,
      "future_positive": 17663
    },
    "S5": {
      "reached": 6112,
      "prefix_positive_excluded": 4340,
      "eligible": 1772,
      "future_positive": 1527
    }
  },
  "2025-08-09": {
    "S3": {
      "reached": 85133,
      "prefix_positive_excluded": 93,
      "eligible": 85040,
      "future_positive": 15373
    },
    "S4": {
      "reached": 85130,
      "prefix_positive_excluded": 93,
      "eligible": 85037,
      "future_positive": 15373
    },
    "S5": {
      "reached": 4834,
      "prefix_positive_excluded": 3390,
      "eligible": 1444,
      "future_positive": 1399
    }
  }
}
```
