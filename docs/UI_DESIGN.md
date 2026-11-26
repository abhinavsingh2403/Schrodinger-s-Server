# UI Design System: "Abyssal Observatory"
**Project:** Schrödinger's Server — Adaptive SSH Deception Research Platform  
**Design Language:** Abyssal Observatory (High-density, scientifically restrained, maritime-slate cybersecurity aesthetics)  
**Specification Version:** 2.0 (November 2026)  

---

## 1. Design Philosophy: 80 / 15 / 5 Rule
- **80% Calm Surfaces & Scientific Clarity:** Deep slate and oceanic abyss background surfaces (`#0B141B` canvas, `#14232C` surface cards), high-contrast legible typography, generous spacing, zero decorative clutter.
- **15% Structural & Semantic Contrast:** Purposeful borders (`#2B4048`), clean badge groupings, clear table grids, subtle inset modules (`#101D25`).
- **5% Visual Drama & Telemetry Pulses:** High-precision data visualizations, SVG metric comparisons, live polling status indicators, and distinct tier transitions (Sea-glass teal `#87C6B9` for T1, Warm brass `#D6B48D` for T2).

---

## 2. Color Palette & Semantic Tokens

```css
:root {
  color-scheme: dark;
  
  /* Canvas & Elevations */
  --canvas: #0B141B;
  --surface: #14232C;
  --surface-elevated: #1B2D35;
  --surface-inset: #101D25;
  
  /* Borders */
  --border-subtle: #2B4048;
  --border-strong: #3E5B66;
  --border-focus: #87C6B9;
  
  /* Text */
  --text-primary: #F0F3EF;
  --text-secondary: #A5B6BA;
  --text-tertiary: #7C9297;
  
  /* Accent Colors */
  --accent-seaglass: #87C6B9;
  --accent-brass: #D6B48D;
  --accent-coral: #D88D81;
  --accent-amethyst: #9A9BCF;
  
  /* Deception Tiers */
  --t1-surface: #23464A;
  --t1-text: #BCE8DC;
  --t1-border: #3B7075;
  
  --t2-surface: #4B392E;
  --t2-text: #E7C7A7;
  --t2-border: #7A5E4D;
  
  --t3-surface: #362C42;
  --t3-text: #D9CCE8;
  --t3-border: #5D4D72;
  
  /* Scientific Verdicts */
  --done-surface: #234538;
  --done-text: #BEE6D2;
  --done-border: #38755C;
  
  --exploratory-surface: #1B3545;
  --exploratory-text: #C3E4F0;
  --exploratory-border: #2D5870;
  
  --invalid-surface: #452A30;
  --invalid-text: #E8ABA6;
  --invalid-border: #7D4750;
  
  --warning-surface: #453B2A;
  --warning-text: #E7CDA0;
  --warning-border: #7B6645;
}
```

---

## 3. Typography & Hierarchy

- **Primary Font Stack:** `ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Monospace Font Stack:** `ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace`
- **Scale:**
  - Page Titles (`h1`): 24px / 700 / letter-spacing: -0.025em
  - Section Headers (`h2`): 18px / 600 / letter-spacing: -0.015em
  - Subheaders (`h3`): 14px / 600
  - Body Copy: 13px / 400 / line-height: 1.55
  - Captions / Meta: 11px / 500 / uppercase tracking: 0.05em
  - Monospace Telemetry: 12px / 400 / line-height: 1.45

---

## 4. Workspaces & Navigation Structure

Top-level navigation connects eight primary investigation workspaces plus one secondary archive:

1. **Mission Control (`/`)** — Live operational overview, polling status ticker, KPI strip, tier escalation monitor, recent session activity stream.
2. **Session Forensics (`/session`)** — 2-column forensic timeline: searchable session selector on left, ordered vertical stage progression (S1–S5) on right, engine compute latency, decision attribute inspector.
3. **Visitor Atlas (`/visitors`)** — Masked recurring visitor trajectories (`vis_...`), multi-session clustering, stage progression distribution, and Docker network bridge loopback IP limitation notice.
4. **Deception Studio (`/deception`)** — Persona comparison (T1 fake shell vs T2 enhanced shell), SVG architecture pipeline diagram, verified transition proof citations, `LAB_DEMO_NOT_ML` explanation, deferred T3 notice.
5. **Model Observatory (`/ml`)** — Exp 0 vs Exp 1 evaluation, stage selector (S2, S4, S5), budget ladders, dynamic SVG charts with random-reference baseline, validity inspector explaining `INVALID` and `INCONCLUSIVE` verdicts, mandatory banner: *"NO VALIDATED ML GAIN"*.
6. **Resource Observatory (`/cost`)** — Matched final-tier lab measurements (mean/max CPU & memory), dynamic SVG chart scaling, repeat-spread range bars, verbatim limitation paragraph from `COST_PER_TIER.md`, zero financial/rupee savings claims.
7. **Evidence Vault (`/evidence`)** — Allowlisted evidence browser, search, active kind filter (`All`, `JSON`, `Markdown`), sort, detail drawer with preformatted Markdown, collapsible JSON tree, copy buttons for paths and raw data.
8. **Lab Console (`/lab`)** — Read-only topology (Cowrie, Gatekeeper, SQLite DB, Dashboard), demo runbook guide, honest display of safety check results (`FAIL` preserved on IPv4 binding, no fake `PASS`), known research boundaries.
9. **Research Archive (`/research`)** — Legacy research interface retained for backward compatibility and test coverage.

---

## 5. Interaction & Accessibility Standards

- **Focus Visibility:** All interactive targets (`a`, `button`, `input`, `select`, `summary`) must define `:focus-visible` with `outline: 2px solid var(--border-focus); outline-offset: 2px;`.
- **Keyboard Traversal:** Complete keyboard navigation for all filters, session selections, evidence drawers, and copy actions.
- **Motion Reduction:** Full `@media (prefers-reduced-motion: reduce)` block nullifying animations and transitions.
- **Copy Actions:** Visual copy buttons for file paths and JSON payloads with temporary `"Copied!"` feedback.
- **Zero AI Slop / Anti-Hallucination:**
  - Never fabricate numbers or metrics; empty states must strictly read `NO DATA` or `NOT RUN`.
  - Negative and inconclusive results must use warning amber/coral tints, never green.
  - No `innerHTML` assignments with dynamic data; strictly DOM nodes and `textContent`.
