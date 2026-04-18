---
name: emil-animations
description: Emil Kowalski's animation and micro-interaction principles for component-level polish. Use when adding animations, transitions, hover states, page transitions, state change effects, or any motion to UI components in the HyperCode dashboard or Course frontend. Also use when reviewing existing animations for quality.
---

# Emil Kowalski — Animation & Micro-Interaction Skill

Based on Emil Kowalski's design engineering philosophy (emilkowal.ski)

---

## Core Rule: Every Animation Needs a "Why"

Before adding ANY animation, answer: **why does this animate?**

Valid reasons:
- **Spatial consistency** — showing where something came from / is going
- **State indication** — communicating a change of state clearly
- **Explanation** — teaching the user what just happened
- **Feedback** — confirming the user's action registered
- **Preventing jarring changes** — softening hard visual cuts

Invalid reason: "it looks cool" — remove it.

---

## NEVER Animate These

```
❌ Keyboard-initiated actions (cmd+k, shortcuts, form submits)
   → Repeated hundreds of times/day. Animation = feels slow.
   
❌ Hover states on mobile
   → No hover on touch. Don't animate what doesn't exist.

❌ Colour changes alone
   → Use transition only if layout/position also changes.

❌ Long animations on repeat actions
   → If it's done 10+ times per session, keep it under 150ms.
```

---

## Spring Values — Use These Exactly

```css
/* Standard spring — most UI interactions */
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

/* Snappy spring — buttons, toggles, chips */
transition: all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);

/* Entrance — elements appearing */
transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);

/* Exit — elements disappearing */
transition: all 0.15s cubic-bezier(0.4, 0, 1, 1);
```

For React/Framer Motion:
```js
// Standard
const spring = { type: "spring", stiffness: 400, damping: 30 }

// Snappy (buttons, toggles)
const snappy = { type: "spring", stiffness: 600, damping: 35 }

// Entrance
const entrance = { type: "spring", stiffness: 300, damping: 25 }
```

---

## Container Status Cards (HyperCode Specific)

Agent health state changes MUST animate:
```tsx
// ✅ RIGHT — state transition with purpose
<motion.div
  animate={{ 
    backgroundColor: status === 'healthy' ? '#22c55e20' : '#ef444420',
    borderColor: status === 'healthy' ? '#22c55e' : '#ef4444'
  }}
  transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
/>

// ❌ WRONG — instant colour snap (jarring)
<div style={{ backgroundColor: status === 'healthy' ? 'green' : 'red' }} />
```

---

## BROski$ Coin Award Animation

This is the most important animation in the ecosystem — the dopamine hit.

```tsx
// Coin count tick-up
const [displayCount, setDisplayCount] = useState(previousBalance)

useEffect(() => {
  const diff = newBalance - previousBalance
  const duration = Math.min(diff * 2, 1500) // cap at 1.5s
  const steps = 20
  const increment = diff / steps
  
  let current = previousBalance
  const timer = setInterval(() => {
    current += increment
    setDisplayCount(Math.round(current))
    if (current >= newBalance) {
      clearInterval(timer)
      setDisplayCount(newBalance)
    }
  }, duration / steps)
}, [newBalance])

// Particle burst on award
<motion.div
  initial={{ scale: 0, opacity: 1 }}
  animate={{ scale: 2, opacity: 0 }}
  transition={{ duration: 0.4 }}
  className="absolute inset-0 rounded-full bg-yellow-400"
/>
```

---

## Page Transitions

```tsx
// Route change — slide + fade
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -8 }}
  transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
/>
```

---

## Button Press Feedback

```tsx
// ✅ Scale press — satisfying, instant
<motion.button
  whileTap={{ scale: 0.97 }}
  transition={{ duration: 0.1 }}
/>

// ❌ No feedback — feels broken
<button onClick={...}>Click</button>
```

---

## Focus Mode Activation (HyperCode Specific)

The `make focus` sequence should feel cinematic:
```
1. Dim non-essential panels (opacity 0→0.2, 300ms)
2. Scale core panel up (1→1.02, spring)
3. Show "HYPERFOCUS" overlay (fade in, 200ms delay)
4. Timer starts (number counts up, no animation)
```

---

## Anti-Patterns

```
❌ bounce easing on anything except playful/game UI
❌ opacity-only animations on layout elements (always pair with translate)  
❌ staggered animations on more than 6 items
❌ animation duration > 400ms (feels broken)
❌ using keyframes when a spring achieves the same result
❌ animating box-shadow (use filter:drop-shadow instead — GPU)
❌ transition: all (always specify the property)
```

---

## Audit Checklist

Before shipping any animated component:
- [ ] Does every animation have a clear purpose?
- [ ] Are keyboard actions animation-free?
- [ ] Do all spring values match the reference above?
- [ ] Are exit animations present (not just entrances)?
- [ ] Does it feel fast? (if in doubt, cut duration by 25%)
- [ ] Tested with `prefers-reduced-motion`?

```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```
