
# 🎨 BROski Hyper Design System (BDS)

**Version:** 1.0
**Philosophy:** "Cyberpunk Dopamine" — High-energy, focus-inducing, and neurodivergent-friendly.

---

## 1. Visual Identity & Vibe

The BROski aesthetic combines **futuristic cyberpunk** elements with **friendly gamification**. It feels like entering a high-tech command center where the AI is your hype-man, not your boss.

-   **Keywords:** Neon, Holographic, Terminal, Dopamine, Focus, Flow.
-   **The Mascot:** "BROski" — A friendly, cap-wearing cyborg agent. Accessible, cool, and supportive.

---

## 2. Color Palette: "Neon Focus"

Designed for dark mode superiority. High contrast for focus, neon accents for dopamine hits.

### 🌌 Base Layers (Backgrounds)
| Name | Hex | Usage |
| :--- | :--- | :--- |
| **Deep Void** | `#0B0418` | Main application background (The infinite space). |
| **Terminal Black** | `#120F1F` | Code blocks, input fields. |
| **Glass Panel** | `rgba(28, 20, 56, 0.75)` | Cards/Panels (requires backdrop-blur). |

### ⚡ Accents (Dopamine Triggers)
| Name | Hex | Usage |
| :--- | :--- | :--- |
| **Hyper Cyan** | `#00F3FF` | Primary borders, active states, focus rings. |
| **Matrix Green** | `#0AFF60` | Success, "Go" signals, code strings. |
| **Electric Purple**| `#BD00FF` | Secondary accents, gradients, "Magic" AI actions. |
| **Hype Pink** | `#FF0099` | Alerts, Errors (but fun), "Hot" items. |

### 📝 Typography Colors
| Name | Hex | Usage |
| :--- | :--- | :--- |
| **Holo White** | `#F0F6FF` | Primary headings and body text. |
| **Dimmed Starlight**| `#A0AEC0` | Secondary text, metadata. |

---

## 3. Typography: "Readable Tech"

Prioritizing readability for neurodivergent minds (Dyslexia-friendly options) while maintaining the tech aesthetic.

### Font Families
1.  **Headings:** `Orbitron` (fallback: `Montserrat`). Bold, futuristic, wide stance.
2.  **Body:** `Inter` (fallback: `OpenDyslexic` option). Clean, tall x-height, indistinguishable characters.
3.  **Code:** `JetBrains Mono` (fallback: `Fira Code`). Ligatures enabled, distinct `0` vs `O`.

### Hierarchy
-   **H1 (The Mission):** 32px, Bold, Hyper Cyan Glow.
-   **H2 (The Chunk):** 24px, Semi-Bold, White.
-   **Body:** 16px, Regular, 1.6 line-height (extra spacing for focus).
-   **Code:** 14px, Monospace.

---

## 4. UI Components & Styling

### 📦 The "Holo-Card" (Core Container)
Every distinct task or information chunk lives in a "Holo-Card" to isolate focus.

```css
.holo-card {
  background: rgba(28, 20, 56, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 243, 255, 0.3);
  border-radius: 12px;
  box-shadow: 0 0 15px rgba(0, 243, 255, 0.05);
  padding: 1.5rem;
  transition: all 0.2s ease-in-out;
}

.holo-card:hover {
  border-color: #00F3FF;
  box-shadow: 0 0 20px rgba(0, 243, 255, 0.2);
  transform: translateY(-2px);
}
```

### 🔘 Buttons (Action Triggers)
-   **Primary (Let's GO):** Hyper Cyan gradient background, Black text, Bold.
-   **Secondary (Chill):** Transparent background, White border, White text.
-   **Shape:** Chamfered edges or Pill-shaped (avoid sharp 90° squares).

### 📟 Data Visualization
-   Use **Neon Borders** to frame charts/maps.
-   **Digital Rain Effect:** Subtle animated matrix code in empty states or loading screens.
-   **Progress Bars:** Chunky, segmented bars (like health bars in games) filled with Matrix Green or Hyper Cyan.

---

## 5. Layout Principles: "The Bento Grid"

To minimize cognitive load, we use a modular "Bento Box" layout.

1.  **Chunking:** The interface is divided into clear, non-overlapping rectangular zones.
2.  **Focus:** One "Active Mission" takes center stage (60% width).
3.  **Support:** Context/Logs/Chat live in collapsible side panels.
4.  **Spacing:** Generous padding (`24px`+) between cards to prevent visual clutter.

---

## 6. Implementation Guidelines

### Responsive Design
-   **Mobile:** Stack the Bento Grid vertically. The "Active Mission" is always top.
-   **Desktop:** 3-column grid. Center stage is focus.

### Accessibility (Non-Negotiable)
-   **Contrast:** All text must pass WCAG AA on the Deep Void background.
-   **Motion:** "Reduce Motion" preference must disable the Matrix Rain and pulsing glows.
-   **Dyslexia Mode:** Toggle class `theme-dyslexic` that swaps `Inter` for `OpenDyslexic`.

### CSS Variables (Snippet)
```css
:root {
  --color-bg: #0B0418;
  --color-primary: #00F3FF;
  --color-secondary: #BD00FF;
  --font-heading: 'Orbitron', sans-serif;
  --font-body: 'Inter', sans-serif;
  --glow-primary: 0 0 10px rgba(0, 243, 255, 0.5);
}
```

---

## 7. Tone of Voice (The "BROski" Persona)

The interface text should match the design energy.

-   **Instead of:** "Processing request..."
-   **Say:** "Cooking that up... 🍳"
-   **Instead of:** "Error 500"
-   **Say:** "Yo, something broke! My bad. 🔥"
-   **Instead of:** "Task Completed"
-   **Say:** "Mission Crushed! +50 Coins 🪙"

---

*This guide serves as the visual constitution for the HyperCode BROski evolution.*
