# 🖥️ BROski Terminal — CLI UI Guide

> **URL:** `http://localhost:3000`
> **Type:** Custom neurodivergent-first CLI interface
> **Last Updated:** 2026-03-25

---

## 🧠 What is BROski Terminal?

BROski Terminal is the **command centre** of HyperCode. It's a custom CLI UI built for ADHD/dyslexic brains — chunked, colourful, fast feedback.

- No walls of text
- Colour-coded status
- Keyboard shortcut everything
- ADHD-friendly chunked output

---

## ⚡ Quick Start

### Open in browser:
```
http://localhost:3000
```

### Or via terminal (if CLI mode enabled):
```bash
docker exec -it broski-terminal bash
```

---

## 🎮 Key Commands

| Command | What it does |
|---------|-------------|
| `status` | Show all agent + service status |
| `agents list` | List all running agents |
| `agents spawn <type>` | Spawn a new agent |
| `agents kill <name>` | Stop an agent |
| `health` | Full system health check |
| `logs <service>` | Tail logs for a service |
| `metrics` | Show live Grafana metrics summary |
| `task new` | Create a new task |
| `task list` | List all tasks |
| `broski coins` | Check your BROski$ balance 💰 |
| `help` | List all commands |

---

## 🎨 UI Features

- **🟢 Green** = service healthy
- **🟡 Yellow** = warning / degraded
- **🔴 Red** = down / error
- **🔵 Blue** = agent activity
- **✨ Sparkle** = evolution event happening

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+H` | Home dashboard |
| `Ctrl+A` | Agents panel |
| `Ctrl+L` | Live logs |
| `Ctrl+M` | Metrics view |
| `Ctrl+T` | Tasks |
| `Ctrl+Q` | Quit/logout |

---

## 🛠️ Config

`services/broski-terminal/config.json`:
```json
{
  "theme": "hyperfocus-dark",
  "font_size": 14,
  "chunk_output": true,
  "max_lines_per_block": 10,
  "api_base": "http://localhost:8000/api/v1"
}
```

---

## 🚨 Troubleshooting

| Problem | Fix |
|---------|-----|
| Terminal blank | Hard refresh `Ctrl+Shift+R` |
| Commands not working | Check HyperCode Core API is up on port 8000 |
| Slow response | Check Redis is running |

---
> **built with WelshDog + BROski 🚀🌙**
