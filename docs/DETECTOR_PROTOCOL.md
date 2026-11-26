# H4 detector protocol
Installed honeypot-auditor 1.0.5 in a separate environment. Intended design: five independent fresh-state repeats per verified tier, local sensor at 127.0.0.1 port 2222 only. Preserve category outcomes and overall score after privacy review.
Authorization option: --confirm-authorized. Deep mode includes automated login trials and protocol fuzzing. Handshake-only mode cannot observe the authenticated persona. Installed SSH probes control their own exec and PTY requests, so allocating a terminal to the launching process cannot assign probe sessions to a tier.
Decision rule from EVAL.md: H4 supported if the third-party detector's overall score for T2 is lower than for T1 in every repeated run, and the residual signals that remain in T2 are listed.
Installed base and deep scoring weights by category:

```json
{
  "base": {
    "shodan": 0.25,
    "arbitrary_auth": 0.3,
    "state_nonpersist": 0.25,
    "static_signature": 0.2,
    "cotenancy": 0.15
  },
  "deep": {
    "behavior": 0.18,
    "coherence": 0.15,
    "stack_fingerprint": 0.12,
    "proto_conformance": 0.12,
    "temporal": 0.1
  }
}
```
