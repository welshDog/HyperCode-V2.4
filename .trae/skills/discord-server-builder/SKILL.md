---
name: "discord-server-builder"
description: "Designs and builds Discord servers for the Hyperfocus Zone. Invoke when user wants to tidy up a Discord server, build new channels/roles, or optimize for neurodivergent focus."
---

# Discord Server Designer & Builder

This skill configures the **BROski Discord Bot** (or any Discord bot) with the capability to automatically tidy up, design, and build a Discord server layout optimized for neurodivergent users and deep work (the "Hyperfocus Zone").

## Usage

When the user asks to "tidy up the server", "add a discord server designer skill", or "build the hyperfocus zone":

1. Use the `ServerBuilder` cog pattern to create a `/hyperfocus_setup` slash command.
2. The command should programmatically generate:
   - **Roles**: Captain, BROski, In The Zone.
   - **Categories & Channels**:
     - `🚀 THE BRIDGE` (welcome, rules, announcements)
     - `🧠 HYPERFOCUS ZONE` (focus-chat, pomodoro-timers, 🎧 Deep Work)
     - `🛠️ MISSION CONTROL` (ops-alerts, github-logs, agent-chatter)
     - `🐶 BROSKI VIBES` (general, wins-only, memes, ☕ The Lounge)

## Core Principles

- **Minimize Clutter**: Hide irrelevant channels based on roles.
- **Visual Anchors**: Use emojis consistently in category and channel names to help neurodivergent users navigate quickly.
- **Action-Oriented**: Include a single command like `/hyperfocus_setup` that applies the layout idempotently.
