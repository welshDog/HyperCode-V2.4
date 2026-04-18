---
name: taste-skill
description: Premium dark UI aesthetic brain for HyperCode and BROski-verse surfaces. Use when designing new pages, dashboards, hero sections, token visualizers, dNFT game UI, or any surface that needs strong visual identity. Enforces dark OLED aesthetics, cinematic motion, and anti-generic patterns. Primary design driver for Mission Control, BROskiPets, and landing pages.
---

# Taste Skill — Anti-Slop Design Brain

The HyperCode aesthetic: **dark. neon. cinematic. hacker-terminal-but-hot.**
No gradients. No Inter font. No 3-column grids. No rounded-everything.

---

## The Aesthetic DNA

```
Colour palette:
  Background:  #000000 or #0a0a0a (true OLED black)
  Surface:     #111111 or #141414
  Border:      #1f1f1f or #262626
  Primary:     #7c3aed (violet — BROski brand)
  Accent:      #06b6d4 (cyan — agent/tech feel)
  Success:     #22c55e
  Warning:     #f59e0b
  Danger:      #ef4444
  Text:        #fafafa (primary), #a1a1aa (muted)

Typography:
  Display:     "Space Grotesk" or "DM Mono" — never Inter/Roboto
  Body:        "Geist" or system-mono for technical content
  Code:        "JetBrains Mono" or "Fira Code"
  
Radius:
  Small UI:    4px (not 8, not 12 — tight and technical)
  Cards:       8px
  Modals:      12px
  Never:       rounded-full on rectangular elements
```

---

## Anti-Slop Rules — NEVER Generate These

```
❌ Purple gradient buttons (bg-gradient-to-r from-purple-500 to-pink-500)
❌ Hero with centred text + gradient background
❌ 3-column feature grid with emoji icons
❌ "Get Started" CTA without visual weight
❌ Glassmorphism blur on everything
❌ Rainbow gradients on text
❌ Animated gradient borders as the primary interaction
❌ Inter/Roboto/Poppins as the headline font
❌ Light mode as the default
❌ Generic SaaS card layout (icon + title + 2-line description)
❌ Bouncy animations on serious UI
❌ Drop shadows in dark mode (use glow instead)
```

---

## What to Do Instead

### Hero Sections
```
✅ Full-bleed dark background
✅ Large, bold, geometric display type (Space Grotesk 700)
✅ One strong accent colour — not a gradient
✅ Real product screenshot or terminal output as the visual
✅ Subtle grid/dot pattern overlay (opacity 3-5%)
✅ CTA: filled button with no gradient, strong border
```

### Cards & Panels
```
✅ Border: 1px solid #1f1f1f — let the border do the work
✅ Background: #111111 — no blur, no glass
✅ Hover: border-color shifts to accent, subtle scale(1.01)
✅ Content-dense — no excessive padding
✅ Monospace numbers for data/stats
```

### Agent Health Cards (HyperCode)
```tsx
// ✅ Technical, data-dense, dark
<div className="border border-[#1f1f1f] bg-[#111] rounded-lg p-4 font-mono">
  <div className="flex items-center gap-2">
    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
    <span className="text-xs text-zinc-400 uppercase tracking-widest">hypercode-core</span>
  </div>
  <div className="mt-2 text-2xl font-bold text-white">HEALTHY</div>
  <div className="text-xs text-zinc-500 mt-1">29/29 containers · 738 MiB</div>
</div>
```

### BROski$ Token Visualizer
```tsx
// ✅ Neon glow on value, monospace, no generic card
<div className="relative border border-violet-500/30 bg-black rounded-lg p-6">
  <div className="absolute inset-0 bg-violet-500/5 rounded-lg" />
  <div className="relative">
    <span className="text-xs text-violet-400 font-mono uppercase tracking-widest">BROski$</span>
    <div className="text-5xl font-bold text-white font-mono mt-1">
      {balance.toLocaleString()}
    </div>
    <div className="text-xs text-zinc-500 mt-2">≈ Level {tier} · {xp} XP</div>
  </div>
</div>
```

---

## Glow System (Use Instead of Shadows)

```css
/* Agent online — green glow */
box-shadow: 0 0 0 1px #22c55e20, 0 0 16px #22c55e10;

/* BROski$ accent — violet glow */
box-shadow: 0 0 0 1px #7c3aed30, 0 0 24px #7c3aed15;

/* Alert/critical — red glow */
box-shadow: 0 0 0 1px #ef444430, 0 0 16px #ef444420;

/* Active/selected — cyan glow */
box-shadow: 0 0 0 1px #06b6d430, 0 0 20px #06b6d415;
```

---

## Motion Rules

```
Entrance animations:  opacity 0→1 + translateY 4px→0 (never more than 4px)
Hover state:          scale(1.01) + border lightens
Active/press:         scale(0.98) — instant, under 100ms
Data updates:         number tick-up (see Emil skill for implementation)
State changes:        colour transition only, 200ms ease-out
```

---

## Layout Principles

```
Grid:       12-column, 24px gutter — technical, not content-marketing
Spacing:    4/8/16/24/32/48 scale only (no arbitrary values)
Density:    COMPACT by default — this is a dev tool, not a landing page
Sidebar:    240px fixed, not collapsible by default
Data:       always monospace, always right-aligned numbers
```

---

## BROskiPets / dNFT Game UI

This surface gets MORE personality:
```
✅ Pixel art elements mixed with dark premium UI
✅ Pet stats in retro-terminal style (green-on-black)
✅ XP bar with glow effect
✅ Rarity colours: Common=grey, Rare=cyan, Epic=violet, Legendary=gold
✅ Particle effects on level-up (subtle, 0.3s max)
✅ Sound design references in comments (even if not implemented)
```

---

## Variance Dial

Set this per surface:
```
Mission Control Dashboard:  variance=LOW (clean, readable under stress)
Landing Page:               variance=HIGH (bold, memorable, wow)
BROskiPets UI:              variance=HIGH (personality, game feel)
Course Frontend:            variance=MED (professional but warm)
Agent Detail View:          variance=LOW (technical, data-dense)
```
