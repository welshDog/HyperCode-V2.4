
# 🎨 BROski Design System Implementation Roadmap

## Overview
Phased rollout of BDS across HyperCode V2.0 interface

---

## Phase 1: Foundation (Week 1) 🏗️

### CSS Variables Setup
**File:** `app/static/css/bds-core.css`
**Time:** 2-3 hours

```css
:root {
  /* Color Palette */
  --deep-void: #0B0418;
  --hyper-cyan: #00F3FF;
  --matrix-green: #0AFF60;
  --ember-orange: #FF6B35;
  --ghost-white: #F5F7FA;
  
  /* Typography */
  --font-heading: 'Orbitron', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-code: 'JetBrains Mono', monospace;
  
  /* Spacing (8px grid) */
  --space-xs: 0.5rem;
  --space-sm: 1rem;
  --space-md: 1.5rem;
  --space-lg: 2rem;
  --space-xl: 3rem;
}
```

### Font Loading
**File:** `app/templates/base.html`
```html
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
```

---

## Phase 2: Component Library (Week 2) 🧩

### Holo-Card Component
**File:** `app/components/HoloCard.tsx` (or Vue/React equivalent)

```tsx
export const HoloCard = ({ children, glow = false }) => (
  <div className={`holo-card ${glow ? 'holo-card--glow' : ''}`}>
    {children}
  </div>
);
```

**CSS:** `app/static/css/components/holo-card.css`
```css
.holo-card {
  background: rgba(11, 4, 24, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 243, 255, 0.2);
  border-radius: 12px;
  padding: var(--space-md);
  transition: all 0.3s ease;
}

.holo-card--glow {
  box-shadow: 0 0 20px rgba(0, 243, 255, 0.4);
}

.holo-card:hover {
  border-color: var(--hyper-cyan);
  transform: translateY(-2px);
}
```

### Priority Components
1. ✅ Holo-Card (container)
2. ✅ Neon Button (primary CTA)
3. ✅ Status Badge (agent health)
4. ✅ Progress Bar (mission tracking)
5. ✅ Code Block (syntax highlighting)

---

## Phase 3: Dashboard Redesign (Week 3) 📊

### Target: `agents/dashboard/index.html`

**Before:** Corporate gray dashboard  
**After:** Cyberpunk command center

**Key Changes:**
- Replace white bg → Deep Void
- Add glassmorphism cards
- Implement Bento Grid layout
- Animate status updates (respects motion prefs)

---

## Phase 4: Accessibility Polish (Week 4) ♿

### Features to Add
1. **Dyslexia Toggle**
   - Button in header
   - Switches to OpenDyslexic font
   - Persists in localStorage

2. **Motion Control**
   - Detect `prefers-reduced-motion`
   - Disable animations if true
   - Keep essential feedback

3. **Contrast Themes**
   - Default (Cyberpunk)
   - High Contrast (WCAG AAA+)
   - Low Saturation (for photosensitivity)

---

## Testing Checklist

### Visual Testing
- [ ] Colors render correctly in all major browsers
- [ ] Fonts load without FOUT/FOIT
- [ ] Glassmorphism works (Safari/Firefox/Chrome)
- [ ] Animations respect motion preferences

### Accessibility Testing
- [ ] Screen reader navigation (NVDA/JAWS)
- [ ] Keyboard-only navigation
- [ ] Color contrast meets WCAG AAA
- [ ] Dyslexia mode functional

### Performance Testing
- [ ] First Contentful Paint < 1.5s
- [ ] Total Blocking Time < 200ms
- [ ] Cumulative Layout Shift < 0.1

---

## Success Metrics

### User Feedback (Target: 90%+ Satisfaction)
- "Feels energetic without overwhelming"
- "Easier to focus for long sessions"
- "Visually distinct from other IDEs"

### Technical Metrics
- Lighthouse Accessibility Score: 95+
- Lighthouse Performance Score: 90+
- Zero critical WCAG violations

---

**Status:** Ready for Phase 1 implementation  
**Next:** Setup CSS variables and font loading
