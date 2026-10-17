---
name: motion
description: Add subtle, accessible Motion for React (motion/react) animations to working ObliGOT screens — staggered entrances, dialog/dropdown transitions, expandable alert details, AI loading transitions — respecting reduced motion and preserving behaviour. Polish only; never a prerequisite.
argument-hint: <screens or interactions to animate>
---

# Motion: $ARGUMENTS

## 1. Inspect
- Read `frontend/package.json` (React/Vite versions, package manager) and the target components.
- Only animate screens that already work. If `motion` is not installed, propose adding the `motion` package and wait for approval; confirm compatibility with the installed React version.
- Import from `motion/react` only.

## 2. Implementation rules
- Put shared variants and easing in one small module (e.g. `src/lib/motion.ts`); reuse them.
- Durations ~150–300 ms; ease-out for entrances, ease-in for exits; small offsets (4–12 px); stagger ≤ 50 ms per item.
- Targets: KPI card stagger, dashboard section reveal, dialog/dropdown enter/exit (`AnimatePresence`), expandable Risk Radar/alert details (animate height/opacity without layout jumps), AI Copilot loading → result transition, restrained hover/tap feedback.
- Respect reduced motion: use `useReducedMotion()` or `MotionConfig reducedMotion="user"`; with reduced motion, use instant or opacity-only changes.
- Never animate fabricated metric changes (no count-up of numbers that did not change in data). Never delay actions, focus, or content availability.
- Avoid flashing, aggressive pulsing, excessive bounce, continuous decorative motion, and layout shift.
- Preserve business logic, routes, styling tokens, API calls, keyboard behaviour, and focus management.

## 3. Verify
- `cd frontend && npm run build` — report the real result.
- Check interactions with animation enabled and with reduced motion emulated; confirm dialogs still trap/return focus and controls remain keyboard-operable. State what was actually checked.

## 4. Report and stop
Changed files, animations added, reduced-motion behaviour, unverified items. Update `IMPLEMENTATION_PLAN.md`. **Stop for approval.**
