---
name: ui-polish
description: Refine the ObliGOT frontend into a calm, information-dense enterprise operations interface — typography, spacing, tables, forms, status indicators, states, accessibility, responsiveness — without changing business logic, routes, or data behaviour.
argument-hint: <pages or areas to polish>
---

# UI polish: $ARGUMENTS

## 1. Inspect
- Read `frontend/src/index.css`, `src/app/App.tsx`, shared components in `src/components/`, and the target pages.
- Note the existing tokens (navy sidebar, teal accent, DM Sans/Manrope), class names, and status/priority colours. Extend them; do not introduce a second design system.

## 2. Goals
- A manager should see the most urgent issue, its owner, due date, and next action within seconds.
- Clear hierarchy: page header → priority work (Today's 5 / alerts) → supporting metrics → details.
- Readable tables: aligned columns, right-aligned numbers, consistent date format, sticky or clear headers, useful search/filters that actually work.
- Consistent status and priority badges with text labels (never colour alone).
- Forms: labels, required markers, inline validation messages, disabled state while saving, confirmation for destructive actions.
- Polished loading, empty (with a next step), error (with retry), and success/confirmation states.

## 3. Accessibility and responsiveness
- WCAG AA contrast, visible `:focus-visible` styles, keyboard-operable menus/dialogs (Escape closes, focus returns), semantic headings, `aria-label` on icon-only buttons.
- Check widths around 375, 768, 1280, and 1440 px: no horizontal page scroll; tables scroll inside their container.

## 4. Avoid
Generic AI-dashboard styling, heavy gradients, glassmorphism, oversized cards or headings, decorative clutter, fake metrics, nonfunctional controls, and changes to API calls, routes, business logic, or data flow.

## 5. Verify
- `cd frontend && npm run build` and report the real result.
- Inspect the changed pages in a running app at the widths above where possible; state which widths were actually checked.

## 6. Report and stop
Changed files, visual changes, accessibility checks done, anything not verified. Update `IMPLEMENTATION_PLAN.md`. **Stop for approval.**
