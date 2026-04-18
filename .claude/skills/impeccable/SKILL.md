---
name: impeccable
description: Design auditor and anti-slop detector. Use when cleaning up existing UI, doing a design review pass, refactoring older components, or before any UI tweaking phase. Run this FIRST on any surface that was built fast and needs polish. Catches AI slop, inconsistencies, accessibility issues, and design drift.
---

# Impeccable — Design Auditor Skill

Based on pbakaus/impeccable. The immune system for your UI.
Run this BEFORE the Taste Skill or Emil animations. Fix first, beautify second.

---

## When to Use

```
✅ Before any UI tweaking session — audit first
✅ On components older than 2 weeks
✅ After a fast-build sprint (anything shipped in < 1 day)
✅ When something "looks off" but you can't say why
✅ Before merging UI PRs
```

---

## /audit — Find Problems

Run a full audit on a component or page. Check for ALL of the following:

### AI Slop Detectors (24 checks)

**Typography:**
- [ ] Is Inter, Roboto, or Poppins used as headline font? → Replace
- [ ] Is font weight only 400 or 500? → Add 700/800 for hierarchy
- [ ] Line length > 75 characters? → Cap at 65ch
- [ ] Missing font-feature-settings for numbers? → Add `font-variant-numeric: tabular-nums`

**Colour & Contrast:**
- [ ] Purple/pink gradient on buttons? → Replace with solid + border
- [ ] Text contrast < 4.5:1? → Fail. Fix immediately.
- [ ] Dark glows as primary decoration? → Use sparingly or remove
- [ ] Colour used as the ONLY state indicator? → Add icon/text too

**Spacing & Layout:**
- [ ] Cramped padding (< 12px on interactive elements)? → Fix to 16px min
- [ ] Inconsistent spacing (mix of arbitrary values)? → Normalise to 4/8/16/24/32
- [ ] Side-tab borders on nav items? → Remove, use background highlight
- [ ] Touch targets < 44px? → Critical. Fix immediately.

**Motion:**
- [ ] Bounce easing (`cubic-bezier(0.34, 1.56, ...)`) on serious UI? → Remove
- [ ] Animation duration > 400ms? → Cut down
- [ ] Animating `box-shadow`? → Switch to `filter: drop-shadow` or glow via outline
- [ ] No exit animation? → Add matching exit

**Structure:**
- [ ] 3-column grid with icon + title + description? → Redesign
- [ ] Generic "hero with centred gradient text"? → Redesign
- [ ] Skipped heading levels (h1 → h3)? → Fix for a11y
- [ ] Missing focus styles on interactive elements? → Add visible focus ring
- [ ] `div` used where `button` should be? → Fix for a11y
- [ ] Images without alt text? → Add descriptive alt
- [ ] Missing aria-label on icon-only buttons? → Add

---

## /normalize — Fix Inconsistencies

After audit, normalise across the component:

1. **Spacing** — Replace all arbitrary Tailwind values with scale values
   ```
   Replace: p-[13px] → p-3 (12px)
   Replace: mt-[18px] → mt-4 (16px) or mt-5 (20px)
   ```

2. **Colour** — Replace all hardcoded hex with CSS variables or Tailwind tokens
   ```
   Replace: #7c3aed → violet-600
   Replace: #111111 → zinc-950 or bg-surface (custom)
   ```

3. **Typography** — Normalise font sizes to scale
   ```
   Replace: text-[13px] → text-sm
   Replace: text-[22px] → text-2xl (24px) — close enough
   ```

4. **Border radius** — Pick ONE value per element type and apply consistently
   ```
   Buttons: rounded (4px)
   Cards: rounded-lg (8px)  
   Modals: rounded-xl (12px)
   Inputs: rounded (4px)
   ```

---

## /polish — Final Pass

After normalize, apply the finishing layer:

1. Add subtle hover states to every interactive element
2. Ensure all status colours have corresponding text (not colour alone)
3. Add `transition-colors duration-150` to all interactive elements
4. Verify loading states exist for all async actions
5. Add empty states for all lists/tables that could be empty
6. Check dark mode variables are applied (no hardcoded light colours)

---

## /distill — Simplify

Remove complexity that isn't earning its place:

```
Remove: Decorative animations that aren't in Emil's valid list
Remove: Gradient text that doesn't improve readability
Remove: Multiple border radius values (pick one per type)
Remove: Nested ternaries in className strings → extract to variables
Remove: Components with > 200 lines → split them
Remove: Props with > 8 items → use a config object
```

---

## HyperCode Specific Patterns to Fix

### Course Frontend (built fast — needs audit)
```
Watch for:
- Hardcoded colours not matching Tailwind config
- Missing error states on API calls
- No loading skeletons (just empty space)
- Inconsistent button sizes across pages
- Mobile padding too tight (< 16px horizontal)
```

### Mission Control Dashboard (older components)
```
Watch for:
- WebSocket data displaying without loading state
- Container names truncating without tooltip
- Stats not using monospace font
- No colour-blind safe alternatives for red/green status
```

---

## Priority Matrix

| Issue | Priority | Why |
|-------|----------|-----|
| Touch target < 44px | 🔴 CRITICAL | Fails WCAG |
| Contrast < 4.5:1 | 🔴 CRITICAL | Fails WCAG |
| Missing focus styles | 🔴 CRITICAL | Keyboard users locked out |
| No error states | 🟠 HIGH | Data loss risk |
| Gradient buttons | 🟡 MED | Design quality |
| Inconsistent spacing | 🟡 MED | Design quality |
| Wrong font | 🟡 MED | Brand consistency |
| Bounce easing | 🟢 LOW | Polish |

Always fix CRITICAL first. Never ship with CRITICAL issues.
