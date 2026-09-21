---
name: ui-ux-design
description: Design or change any project UI; requires a brief, reusable tokens, accessible states, and multi-width visual verification before coding is considered done.
---

# UI/UX design

Reason before coding. Focus on the one or two screens judges will see.

1. Write a 5-8 line brief in `docs/DESIGN.md`: user, main task, three tone adjectives, one reference direction, and demo screens.
2. Define tokens before components: WCAG AA palette pairs, type scale, 4/8 px spacing scale, radii, and shadows. Implement them as CSS variables or theme values; never hard-code tokens in components.
3. Establish hierarchy with one primary action per screen, generous whitespace, mobile-first responsiveness, and consistent components.
4. For every interactive component define: default, hover, focus-visible, active, disabled, loading, empty, and error states where applicable.
5. Verify contrast, keyboard navigation, labels, alt text, and that meaning never relies on color alone.
6. Avoid generic AI styling: purple gradients by default, emoji icons, cluttered card grids, lorem ipsum, and unstyled default fonts. Choose one clean, restrained direction and keep it coherent.
7. Build the demo path first; defer screens judges will not see unless the MVP needs them.
8. Run the app and use Playwright to capture 375, 768, and 1440 px screenshots. Inspect and fix each before declaring completion.
9. Append non-obvious design choices and reasons to `docs/DECISIONS.md`.

Do not choose a framework or add a heavy dependency without human approval.
