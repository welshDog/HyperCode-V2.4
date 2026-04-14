# Claude Auto-Discovery (.claude/)

This folder contains Claude's local project configuration and reusable skill modules.

## Entry Points

- Project intelligence: [CLAUDE.md](file:///h:/HyperStation%20zone/HyperCode/HyperCode-V2.4/CLAUDE.md)
- Claude permissions + MCP config: [settings.local.json](file:///h:/HyperStation%20zone/HyperCode/HyperCode-V2.4/.claude/settings.local.json)
- Claude skill modules (auto-discovered): [skills/](file:///h:/HyperStation%20zone/HyperCode/HyperCode-V2.4/.claude/skills/)

## Skill Discovery Rules

- Claude skills live under `.claude/skills/<skill-name>/SKILL.md`.
- Each `SKILL.md` starts with YAML frontmatter (`name`, `description`) used for matching.

## Local Skill Packs

- `broski-discord-bot-skill/` is a standalone skill pack with its own docs, examples, and Dockerfile.
- A Claude-discoverable wrapper skill is provided under `.claude/skills/` for consistent discovery.

> ⚠️ **Working system:** HyperCode-V2.4 (not V2.0). All paths, ports and agent names are the same.
