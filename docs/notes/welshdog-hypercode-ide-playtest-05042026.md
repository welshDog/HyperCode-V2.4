WelshDog HyperCode IDE — Full Playtest Report 🧪
Tested every nav tab, panel, button, and interactive element. Here's the full breakdown bro:

✅ WHAT'S WORKING
Hyper Station (Home)
Metrics Home panel — Live data streaming: API Requests/min, Avg Response (ms), Active Agents, Error Rate all updating in real-time

Agents panel — All 3 agents (healer-agent, hypercode-core, celery-worker) showing HEALTHY with LVL 1 and XP bars displayed

BROski Pulse panel — BROski$ (12), Healthy 3/3, healer-agent as Top Agent all rendering correctly

Focus mode on panels — Working perfectly. Click Focus → panel expands full width, others dim, Exit Focus button appears and works

Tasks panel — Input field renders correctly, + button visible

IDE Tab
Files panel — Loads /workspace breadcrumb navigation, renders correctly

Editor panel — Shows "Select a file to view details" placeholder appropriately

BROski + Metrics sidebar — Metrics and BROski stats display on the IDE page too (great persistent context!)

Terminal (Orchestrator Task Runner) — Accepts input, Run button works, echoes command to output area

Agents Tab
Agents Status Board — All 3 agents load with HEALTHY badges, XP bars, levels

Mission Tab
6-panel grid loads: Agent Swarm, Event Timeline, Metrics, Tasks, System Logs, BROski Pulse

System Logs — "Live" indicator and "No log entries yet — system warming up…" — correctly initialised

Mission view modes (Grid/Focus/Present) — Buttons present in navbar; Focus mode triggers proper data load for all panels

Plan Generator — UI works, text input resizable, Generic/PRD/Issue/Design dropdown options all present

BROski Pulse on Mission — Once Focus mode loaded, shows correct 3/3 Healthy and BROski$ 12

Health Tab
Docker + Service Health — Core (HEALTHY), Healer (HEALTHY) confirmed

Live checks via /api/* — Timestamps display correctly

Refresh button — Works, timestamps update on click

Themes
Dyslexia — Selected and active (shown as default on load)

High-C — Adds white borders/outlines to all panels for contrast — functional

All 4 theme toggles — Clickable and switch state correctly

🐛 BUGS FOUND
#	Location	Issue	Severity
1	Tasks Panel (all pages)	Enter key does NOT submit a task — text is typed, Enter fires, input clears but task never appears in list. "No tasks yet" persists	HIGH
2	MCP Tab	Returns ⚠️ signal is aborted without reason after loading — MCP Gateway is offline/crashing	HIGH
3	IDE → Files Panel	⚠️ Filesystem tools unavailable (MCP adapter offline) — Files can't be browsed because MCP is down (linked to bug 2)	HIGH
4	IDE → Terminal	Command runs, input echoes to output (> list all files in workspace) but zero response returned — agent not replying	MEDIUM
5	Mission → Plan Generator	Returns ⚠️ Could not validate credentials — API key not set/connected	MEDIUM
6	Mission Grid view (initial load)	Agent Swarm shows \u23F3 Loading agents... and Metrics shows \u23F3 Loading metrics... with unicode escape codes rendered as literal text instead of the hourglass emoji ⏳	LOW
7	Mission → BROski Pulse (Grid view)	Shows BROski$ = 0 and Healthy = 0/0 on initial load — data inconsistent with Hyper Station (which shows 12 and 3/3). Fixes itself after switching to Focus mode	MEDIUM
8	Health → Crew Orchestrator	Status shows UNKNOWN with no timestamp — Crew Orchestrator not reporting health	MEDIUM
9	Health → Services section	Empty — no services listed below the 3 cards	LOW
10	Dyslexia theme	Visually identical to Default — no OpenDyslexic font or visual distinction applied	MEDIUM
11	Focus vs Present modes (Mission)	Both look identical — Present mode has no visible difference (should it go fullscreen or slide-deck style?)	LOW
12	Agents tab	Clicking an agent card does nothing — no expand/detail/logs view	LOW
💡 RECOMMENDATIONS — Missing Panels & Features
🔴 Priority Fixes First
Fix Task submission — check the onKeyDown handler for Enter key, likely event not being caught or API call failing silently

MCP adapter — needs to be running for Files panel and IDE terminal to work. Check if the MCP Docker container is up (docker ps)

Set API key for Plan Generator (Anthropic/OpenAI key in .env)

Dyslexia theme — swap in OpenDyslexic or similar font, increase letter-spacing and line-height

🟡 Missing Panels to Add
Panel	Tab	Why
Git Panel	IDE	Show branch, uncommitted changes, last commit — massive for dev flow
Agent Detail / Logs drawer	Agents	Click an agent → expand to see its logs, last action, uptime, restart button
Redis Queue Monitor	Hyper Station / Mission	Queue depth is shown but no queue items visible — add a queue inspector
Docker Container Status	Health	The Services section is empty — pipe in docker ps status for each container
XP History / Level-up Log	Hyper Station	BROski Pulse has XP=0 and agents at LVL 1 but nothing explaining how to level them up
Hyperfocus Timer	Hyper Station / IDE	A
WelshDog HyperCode IDE - Full Playtest Report 🎮
✅ WHAT'S WORKING WELL
Navigation & Routing
All 6 nav tabs route correctly: / /ide /agents /mission /mcp /health

Active tab highlighting works perfectly

Navigation is instant with no page flicker

Hyper Station (Home Dashboard)
Metrics Home panel: Live data updating - API Requests/min, Avg Response (ms), Active Agents (3), Error Rate (0%), Redis Queue Depth (0) all displaying correctly

Agents panel: All 3 agents (healer-agent, hypercode-core, celery-worker) showing HEALTHY with LVL 1 and XP bars

BROski Pulse: BROski$ (12), Healthy 3/3, Top Agent = healer-agent - all live

Focus mode on panels: Works great - expands single panel, dims others, shows "Exit Focus" button

IDE Tab
Three-panel layout (Files, Editor, BROski + Metrics sidebar) renders correctly

Terminal (Orchestrator Task Runner) at bottom - accepts input and logs commands

Breadcrumb navigation (/workspace /) is present

BROski + Metrics sidebar mirrors home dashboard data live

Agents Tab
Clean status board showing all 3 agents with HEALTHY status, level and XP bars

Mission Tab
Rich multi-panel layout: Agent Swarm, Event Timeline, Metrics, Tasks, System Logs, BROski Pulse, Plan Generator

View mode switcher works: Grid / Focus / Present buttons in top bar

System Logs panel shows "Live" status and "No log entries yet - system warming up..."

Plan Generator has a working dropdown with 4 options: Generic, PRD, Issue, Design

BROski Pulse on Mission syncs correctly once data loads

Health Tab
Docker + Service Health panel with live checks via /api/*

Core = HEALTHY, Healer = HEALTHY (with timestamps)

Refresh button works - timestamps update on click

Themes
Dyslexia mode: Active and selectable

High-C mode: Adds white borders/outlines to panels for high contrast

Default/Focus/Present modes: Working

🐛 BUGS FOUND
#	Location	Issue	Severity
1	Tasks panel (all pages)	Pressing Enter doesn't create tasks - input clears but "No tasks yet" remains	HIGH
2	Tasks panel	+ button clears input without creating the task	HIGH
3	IDE > Files panel	"Filesystem tools unavailable (MCP adapter offline)" - file browser broken	HIGH
4	IDE > Terminal	Commands echo to output but return no response from orchestrator	HIGH
5	MCP tab	"signal is aborted without reason" - MCP Gateway fully offline	HIGH
6	Mission > Plan Generator	"Could not validate credentials" - API key not configured	MED
7	Mission > Event Timeline	Shows "Disconnected" on initial Grid load (resolves in Focus/Present view)	MED
8	Mission > BROski Pulse	Shows 0/0 Healthy and BROski$ 0 on initial Grid load - data race condition	MED
9	Health > Crew Orchestrator	Status = UNKNOWN (no timestamp), not reporting health	MED
10	Health > SERVICES section	Empty - no services listed under the Services header	LOW
11	Themes: Dyslexia mode	No visible font change (should load OpenDyslexic or similar) - looks identical to Default	MED
12	Themes: Focus vs Present mode	On Mission tab these look identical - Present mode not visually distinct	LOW
13	Agents tab	Clicking an agent card does nothing - no detail/expand view	LOW
💡 MISSING PANELS & RECOMMENDATIONS
Missing Panels I'd Add:
1. Git / Version Control Panel (IDE tab)

Show current branch, uncommitted changes, last commit

Quick commit/push buttons

Neurodivergent-friendly: no need to context-switch to terminal for git ops

2. Hyperfocus Timer Panel (Hyper Station)

Pomodoro-style timer built for ADHD hyperfocus sessions

"Currently in focus session" status with break reminders

Could award BROski XP for completing sessions

3. Agent Logs / Activity Feed (Agents tab)

When you click an agent, show its recent activity, logs, last task, errors

Right now agents are just names + status badges - no drilldown

4. MCP Tools Browser (MCP tab)

When MCP comes back online, show registered tools, their descriptions, test buttons

Right now the page is basically empty even when it works

5. Docker Container Monitor (Health tab)

Show running containers (not just Core/Crew/Healer), their CPU/RAM usage

You already use Docker heavily - this would be gold for you

6. Redis Queue Inspector (Mission tab or new tab)

Redis Queue Depth shows 0 in metrics but no way to see what's queued

Would help debug agent task flow

7. Settings / Config Panel (new tab or sidebar)

API key configuration (so Plan Generator actually works)

Theme persistence

Agent config (which agents to enable, polling intervals)

MCP adapter endpoint configuration

8. Notifications / Alerts Panel

Right now errors are silent except in the terminal output

A toast/notification system for agent failures, health alerts, task completions

🎯 Priority Fix Order
text
1. FIX: Tasks panel Enter key submission (quick win)
2. FIX: MCP adapter connection (unlocks IDE file browser + MCP tab)
3. FIX: API credentials for Plan Generator
4. FIX: Mission tab data race - Grid view loading order
5. FIX: Dyslexia theme font (load OpenDyslexic)
6. ADD: Agent detail drilldown on click
7. ADD: Hyperfocus timer panel
8. ADD: Git panel in IDE
Overall Vibe Check
The foundation is solid bro - live metrics updating, 3 agents all healthy, Focus mode working, routing clean. The dashboard feels like a proper IDE. Main things holding it back right now are the MCP adapter being offline (takes down the file browser AND the MCP tab), and the Tasks panel not actually submitting. Sort those two and you've got a genuinely usable v0.1 to show people. The BROski gamification layer (XP, levels, BROski$) is a great differentiator - just need to wire up the XP so it goes above 0.