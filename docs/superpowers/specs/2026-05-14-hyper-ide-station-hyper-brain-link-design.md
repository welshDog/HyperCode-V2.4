# Hyper IDE Station → Hyper Brain Link (Design)

## Goal
Add a top-bar button in Hyper IDE Station that opens the Hyper Brain Command Center at `http://localhost:8100/ui` in a new tab.

## Placement
- Top bar, right side, before notification controls
- Label: `🧠 Hyper Brain`

## Behavior
- Opens in a new tab (`target="_blank"`)
- Uses `NEXT_PUBLIC_HYPER_BRAIN_URL` when set (embedded at dashboard build time)
- Otherwise falls back to a safe local default (`http://localhost:8100/ui` or `http://127.0.0.1:8100/ui` when applicable)

## Non-goals
- No sidebar nav item
- No runtime configuration (requires rebuild to change `NEXT_PUBLIC_HYPER_BRAIN_URL`)
- No auth or availability checks
