# UI Design System Specification

## Palette Tokens
- `--bg-canvas`: `#040711` (terminal near-black base background)
- `--bg-surface`: `#0b111e` (card surface elevation)
- `--bg-subtle`: `#060a13` (inset container background)
- `--border-subtle`: `#1a2639` (default perimeter border)
- `--border-strong`: `#324863` (interactive element border)
- `--text-primary`: `#edf3ff` (contrast ratio > 12:1 against canvas)
- `--text-muted`: `#94a3b8` (contrast ratio > 4.5:1 against canvas)
- `--accent-cyan`: `#38bdf8` (restrained telemetry highlight)
- `--accent-focus`: `#56c7ed` (visible 2px focus ring)

## Type Scale & Typography
- Font stack body: `ui-sans-serif, system-ui, -apple-system, sans-serif`
- Font stack code/telemetry: `ui-monospace, SFMono-Regular, Menlo, monospace`
- Hierarchy: Title 24px/700, Subtitle 18px/600, Section 15px/700, Body 13px/400, Caption 11px/600

## Spacing & Responsive Grid
- 4px baseline increments: 4px, 8px, 12px, 16px, 24px. Minimum phone width: 360px.
- No page-level overflow: tables wrap in `.scroll` container with `-webkit-overflow-scrolling: touch`.

## Status Chips & Verdict Colors (Honest Encoding)
- `DONE` / `RECORDED`: `#0f3d2e` bg, `#baffd8` text, `#34a87c` border (verified completed artifacts)
- `EXPLORATORY`: `#123d55` bg, `#abedff` text, `#56c7ed` border (in-progress / observational)
- `INVALID`: `#3d1a1a` bg, `#fca5a5` text, `#f87171` border (neutral-warning, never green)
- `INCONCLUSIVE` / `NOT RUN`: `#3d2812` bg, `#fed7aa` text, `#fb923c` border (amber caveat)

## Tier Visual Indicators
- T1 Lite: `#123d55` bg, `#abedff` text, `#56c7ed` border
- T2 Hardened: `#3d2812` bg, `#fed7aa` text, `#fb923c` border
- T3 Real VM: `#331a47` bg, `#e9d5ff` text, `#c084fc` border

## Motion & Accessibility Rules
- `prefers-reduced-motion: reduce`: disable non-essential transitions and pulsing.
- Only polling endpoints show live ticker; static evidence remains completely motionless.
- Full keyboard focus: `:focus-visible` with 2px outline and 2px offset on all interactive targets.
- Landmarks: `<nav>`, `<header>`, `<main>`, `<footer>` with `aria-live="polite"` status containers.
