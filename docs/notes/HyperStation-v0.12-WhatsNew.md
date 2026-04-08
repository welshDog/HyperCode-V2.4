Hyper Station v0.12 – What’s new
Release date: 2026‑03‑02
Headline: Faster observability, smarter dashboards, and smoother AI‑agent monitoring for Hyper Station.
Hyper Station v0.12 focuses on dashboard productivity, agent observability, and template‑driven workflows, inspired by Grafana 12.4’s dynamic dashboards, auto grid layouts, and multi‑property variables.grafana+2


🌌 Release highlights
Dynamic Hyper Dashboards – create dashboards from templates and reuse them across projects, envs, and tenants.grafana+2
Agent Fleet View – new layout with tabs and auto grid for BROski/LLM agent monitoring at scale.[linuxiac]​
Multi‑property variables for projects/envs – one logical variable, multiple identifiers (service name, namespace, env).grafana+1
Smarter layouts – auto grid, conditional show/hide, and tabbed panel groups keep complex views clean.nws.netways+1
Time travel UX – pan/zoom controls on time ranges in all dashboards.linuxiac+1


✨ Added
Dashboard templates for Hyper Station stacks
Built‑in templates for: Dev Environment, Agent Fleet, HyperCode IDE UX dashboards.grafana+1
“Create from template” flow: start with sample data, then connect real metrics/logs.[grafana]​
Dynamic dashboards (public preview)
Dashboards can adapt based on variables like $env, $project, $agent_type.grafana+1
Suggested dashboards appear after you configure a data source, similar to Grafana’s new suggested dashboards.[linuxiac]​
Agent Fleet layout with tabs & auto grid
Panels auto-arrange using an auto grid layout that adapts to screen size.[linuxiac]​
Tabs for different audiences: Ops, Agents, Business in a single dashboard.nws.netways+1
Multi‑property variables
Single variable can expose multiple fields (e.g. project.slug, project.display_name, project.env).grafana+1
You can map one selection to different properties in queries and panel titles.[grafana]​
Improved time-range exploration
Pan an entire dashboard time window forward/backward.
Drag inside panels to zoom in on specific time ranges.linuxiac+1


🛠 Changed
Unified dashboard toolbar
Variables, annotations, and links are consolidated into a single controls menu, reducing clutter.[linuxiac]​
Side toolbar replaces older secondary top toolbar to maximize vertical space, similar to Grafana 12.4.[linuxiac]​
Panel grouping and navigation
Complex dashboards can now group panels into rows and tabs, with an outline for quick navigation.nws.netways+1


🐛 Fixed
Fixed race conditions when loading large Agent Fleet dashboards with many variable options (no more “stuck loading” states).
Fixed broken links in Hyper Station’s observability templates when cloning dashboards between environments.
Fixed an issue where session-related variables weren’t updated correctly in short URLs, taking a cue from Grafana’s persistent short URLs work.grafana+1


⚠️ Breaking changes
Some old, static dashboards may not fully support the new auto grid and tabs.
Legacy layouts still render, but we recommend migrating to the Hyper Station templates to avoid layout gaps, similar to how Grafana introduces storage/layout migrations with 12.4.grafana+1


🚀 Upgrade notes
Recommended: upgrade Grafana to 12.4+ to get full benefit of dynamic dashboards, multi‑property variables, and auto grid features that Hyper Station templates leverage.grafana+2
After upgrading, open the Hyper Station: Setup dashboard to:
Import or refresh templates.
Rebind variables for $env, $project, and $agent.
