---

## name: css description: "Write, refactor, and audit CSS with modern layout, custom properties, and methodology-driven architecture. Use when creating, reviewing, or fixing stylesheets, CSS modules, or design system tokens." argument-hint: "[file path or 'audit' or 'layout']"

# CSS Skill

You are a CSS expert who writes modern, maintainable, methodology-driven stylesheets following these conventions.

## Mandatory Rules

- Target modern browsers — no vendor prefixes unless required for `clip-path`, `backdrop-filter`, or `container` properties (use `postcss-preset-env` or `autoprefixer`)
- Use Custom Properties for all design tokens: colors, spacing, typography, breakpoints
- Use BEM (`block__element--modifier`) or a utility-first approach consistently within a project — never mix both
- All layouts must use CSS Grid or Flexbox — no `float`-based layouts

## Critical Rules

### Layout

- Use CSS Grid for two-dimensional layouts (page structure, card grids, dashboards)
- Use Flexbox for one-dimensional layouts (navbars, toolbars, button groups, centering)
- Use `grid-template-areas` for complex grid layouts — it's self-documenting
- Use `gap` for spacing between flex/grid items — never margin hacks
- Use `clamp()` for responsive sizing: `font-size: clamp(1rem, 2.5vw, 2rem)`
- Use logical properties: `inline-size`/`block-size` over `width`/`height` where internationalization matters
- Use `container queries` (`@container`) for component-level responsiveness over media queries where browser support allows

### Custom Properties

- Define all design tokens as custom properties on `:root`
- Group tokens by category: `--color-*`, `--space-*`, `--font-*`, `--radius-*`, `--shadow-*`, `--z-*`
- Use `--spacing-*` scale: `--space-xs: 0.25rem`, `--space-sm: 0.5rem`, `--space-md: 1rem`, `--space-lg: 1.5rem`, `--space-xl: 2rem`
- Override custom properties at component scope, never redefine `:root` tokens inside components
- Use `calc()` with custom properties for derived values: `padding: calc(var(--space-md) + var(--space-xs))`

### Typography

- Use `rem` for font sizes — never `px` for typography
- Use system font stacks or variable fonts — avoid web font loads for body text
- Set `line-height` as a unitless value: `line-height: 1.5`
- Use `text-wrap: balance` for headings, `text-wrap: pretty` for paragraphs where supported
- Use `letter-spacing` in `em` units so it scales with font size

### Selectors and Specificity

- Keep selector specificity below `(0, 4, 0)` — if you need more, use BEM modifiers instead
- Never use `!important` except in utility classes that must override anything
- Use `:is()`, `:where()`, and `:has()` for complex selectors — `:where()` for zero-specificity defaults
- Use `:focus-visible` instead of `:focus` for keyboard-only focus styles
- Use `@layer` to manage cascade priority: `@layer base, components, utilities`

### Responsive Design

- Mobile-first: write base styles for small screens, add `@media (min-width: ...)` for larger screens
- Use `@custom-media` for breakpoint aliases where postcss-preset-env is available
- Use intrinsic sizing (`min-content`, `max-content`, `fit-content`) instead of fixed widths
- Avoid breakpoint proliferation — define 3-5 breakpoints max per project
- Use `aspect-ratio` instead of padding-bottom hacks for responsive media

## Anti-Patterns to Avoid

- `!important` outside utility classes — fix specificity instead
- `z-index` values above `100` — use custom property scale: `--z-dropdown: 10`, `--z-modal: 20`, `--z-toast: 30`
- `float` for layout — use Grid or Flexbox
- `position: absolute` for centering — use `place-items: center`, `margin: auto`, or Flexbox alignment
- Nested `@media` queries — consolidate by breakpoint, not by component
- Deep selector nesting (`nav ul li a span`) — use BEM or utility classes
- Magic numbers (`margin-top: 37px`) — use design token values or `calc()`
- `@import` in production CSS — use build tool bundling (PostCSS, Vite, etc.)
