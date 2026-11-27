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

Primary navigation: Mission Control, Session Forensics, Visitor Atlas, Deception Engine, Model & Research.

Evidence & Proof footer: Evidence Vault, Resource Observatory, Replay, Detector, Lab Console, Research Archive.

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
