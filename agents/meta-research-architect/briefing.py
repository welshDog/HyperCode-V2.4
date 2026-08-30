"""Turn a list of papers into a BROski-style brief and fan it out to sinks.

Sinks (each optional, each best-effort — one failing never blocks the others
or the HTTP response):
  * Redis   - store `research:latest`, publish to `hypercode_research`
  * Discord - POST the markdown to a webhook
  * Vault   - drop a markdown note so the Obsidian brain graph / RAG ingests it
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import httpx

import config
from models import BriefResult, Paper

logger = logging.getLogger(__name__)

_SUMMARY_CHARS = 320


def _chunk_summary(text: str) -> str:
    text = text.strip()
    if len(text) <= _SUMMARY_CHARS:
        return text
    return text[:_SUMMARY_CHARS].rsplit(" ", 1)[0] + "..."


def render_markdown(kind: str, papers: list[Paper], *, topic: str | None, window: str,
                    categories: list[str], new_count: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = []
    if kind == "topic":
        lines.append(f"# Research Brief - {topic}  ({today})")
        lines.append("")
        lines.append(f"**Categories:** {', '.join(categories)} - **Sources:** {len(papers)}")
    else:
        lines.append(f"# Weekly Research Brief - {today}")
        lines.append("")
        lines.append(
            f"**Window:** {window} - **Categories:** {', '.join(categories)} - "
            f"**New papers:** {new_count}"
        )
    lines.append("")

    if not papers:
        lines.append("_No new papers matched this sweep._")
        return "\n".join(lines)

    lines.append("## Top picks")
    lines.append("")
    for i, p in enumerate(papers, 1):
        authors = ", ".join(p.authors[:4]) + (" et al." if len(p.authors) > 4 else "")
        lines.append(f"### {i}. {p.title}")
        lines.append(f"- **Authors:** {authors or 'n/a'}")
        lines.append(f"- **Gist:** {_chunk_summary(p.summary)}")
        lines.append(f"- **Link:** {p.url}")
        lines.append("")

    lines.append("## Next step (human decides)")
    lines.append("")
    lines.append(
        "Phase 1 is observe-only. Pick at most **one** pattern above worth trialling, "
        "then raise it with mission-director - this agent proposes nothing on its own."
    )
    return "\n".join(lines)


async def _sink_redis(result: BriefResult) -> str:
    try:
        import redis.asyncio as aioredis
    except ImportError:  # pragma: no cover
        return "skipped: redis lib missing"
    client = aioredis.from_url(config.REDIS_URL, socket_connect_timeout=3, socket_timeout=3)
    try:
        payload = result.model_dump_json()
        await client.set(config.REDIS_LATEST_KEY, payload)
        await client.publish(config.REDIS_CHANNEL, payload)
        return "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis sink failed: %s", exc)
        return f"error: {exc}"
    finally:
        await client.aclose()


async def _sink_discord(result: BriefResult) -> str:
    if not config.DISCORD_WEBHOOK_URL:
        return "skipped: no webhook configured"
    # Discord hard-caps message content at 2000 chars.
    content = result.markdown
    if len(content) > 1900:
        content = content[:1900].rsplit("\n", 1)[0] + "\n... (truncated - see vault note)"
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(config.DISCORD_WEBHOOK_URL, json={"content": content})
            resp.raise_for_status()
        return "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Discord sink failed: %s", exc)
        return f"error: {exc}"


def _sink_vault(result: BriefResult) -> str:
    if not config.VAULT_DIR:
        return "skipped: no vault dir configured"
    try:
        os.makedirs(config.VAULT_DIR, exist_ok=True)
        stamp = result.generated_at.strftime("%Y-%m-%d-%H%M")
        slug = (result.topic or "weekly").lower().replace(" ", "-")[:40]
        path = os.path.join(config.VAULT_DIR, f"Research-Brief-{slug}-{stamp}.md")
        frontmatter = (
            "---\n"
            f"created: {result.generated_at.isoformat()}\n"
            "source: meta-research-architect\n"
            "type: research-brief\n"
            f"kind: {result.kind}\n"
            "tags: [research, arxiv, auto]\n"
            "---\n\n"
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(frontmatter + result.markdown + "\n")
        return f"ok: {path}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vault sink failed: %s", exc)
        return f"error: {exc}"


async def deliver(result: BriefResult) -> BriefResult:
    """Fan the brief out to every configured sink; record each outcome."""
    result.sinks = {
        "redis": await _sink_redis(result),
        "discord": await _sink_discord(result),
        "vault": _sink_vault(result),
    }
    logger.info("brief delivered kind=%s new=%s sinks=%s",
                result.kind, result.new_count, json.dumps(result.sinks))
    return result
