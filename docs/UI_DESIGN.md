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

---

## 6. Extended Tokens & Shared Component System

### Extended Design Tokens
```css
/* Typography Scale */
--text-xs: 0.6875rem; /* 11px */
--text-sm: 0.8125rem; /* 13px */
--text-base: 0.9375rem; /* 15px */
--text-lg: 1.125rem; /* 18px */
--text-xl: 1.375rem; /* 22px */
/* Spacing Scale (4px/8px rhythm) */
--space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-6: 24px; --space-8: 32px;
/* Radii & Motion */
--radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px;
--duration-fast: 150ms; --duration-base: 250ms; --duration-slow: 400ms;
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
/* Elevation & Z-Index */
--z-base: 1; --z-dropdown: 20; --z-sticky: 40; --z-modal: 100; --z-tour: 200;
```

### Shared Components Specification
- **Page Header & Banner**: Top banner with scope, policy profile, and demo label; sticky header with 5-link primary nav.
- **Card & Inset Surface**: Bordered containers (`--border-subtle`), elevated backgrounds (`--surface`), rounded corners (`--radius-md`).
- **Status & Verdict Chips**: Scoped styling for T1, T2, done, exploratory, INVALID, INCONCLUSIVE, NOT RUN.
- **Interactive Scrubber**: Draggable stage scrubber with play/pause/step controls and keyboard arrows.
- **Tooltip & Popover**: Accessible focus/hover info cards with sourced explanation text only.
- **Collapsible Drawer / Section**: `<details>`/`<summary>` disclosure widgets with keyboard support.
- **Telemetry & Funnel Legend**: Distinct SVG color swatches and text descriptions.
- **Empty / Error / Loading States**: Explicit skeleton pulse and "NO DATA" / "NOT RUN" placards.
- **Print Stylesheet**: Black-on-white high contrast print view for Mission Control and Model & Research.

