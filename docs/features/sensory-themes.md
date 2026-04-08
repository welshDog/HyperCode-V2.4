# 🎨 Sensory Theme System

> Neurodivergent-first theming for HyperCode V2.0 — because your environment should work FOR your brain.

## Three Presets

| Theme | Best For | Motion | Font | Palette |
|---|---|---|---|---|
| 🌙 **CALM** | Sensory sensitivities, autism, migraine | None | OpenDyslexic | Muted slate |
| 🎯 **FOCUS** | ADHD deep work, general use | Minimal | JetBrains Mono | High-contrast cyan |
| ⚡ **ENERGISE** | High-energy hyperfocus, creative sprints | Full | JetBrains Mono | Vibrant purple/pink |

## How It Works

1. **User picks a theme** via the `SensoryThemeSwitcher` component in the dashboard header
2. **`data-hc-theme` attribute** is set on `<html>` — all CSS custom properties update instantly
3. **Preference is saved** to `localStorage` under key `hc-sensory-theme`
4. **On next load**, saved preference is restored automatically
5. **OS preference respected** — if `prefers-reduced-motion: reduce` is set AND no saved preference exists, CALM is auto-selected

## User Config File

Advanced users can set preferences in `~/.hypercode/sensory_profile.json`:

```json
{
  "theme": "calm",
  "motion": "none",
  "font": "opendyslexic",
  "contrast": "high",
  "colour_saturation": 0.4,
  "letter_spacing": "wide",
  "line_height": 1.9
}
```

Schema: `config/sensory_profile.schema.json`

## OpenDyslexic Font Setup

The CALM theme uses OpenDyslexic by default. To enable it:

```bash
# Download from https://opendyslexic.org/ (free, SIL OFL licence)
# Place the .otf file in:
cp OpenDyslexic-Regular.otf agents/dashboard/public/fonts/
```

## WCAG Compliance

- CALM theme: **WCAG 2.2 AAA** (7:1 contrast ratio, no motion, dyslexia font)
- FOCUS theme: **WCAG 2.2 AA** (4.5:1+)
- ENERGISE theme: **WCAG 2.2 AA** (tested at 4.5:1+ on active elements)
- All themes: `prefers-reduced-motion` and `prefers-contrast: more` overrides applied

## Adding a Custom Theme

1. Add a new `[data-hc-theme='yourtheme']` block in `sensory-themes.css`
2. Add the entry to the `THEMES` array in `SensoryThemeSwitcher.tsx`
3. Add the value to the `theme` enum in `config/sensory_profile.schema.json`
4. Done! No other changes needed.
