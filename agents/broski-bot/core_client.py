"""
BROski Bot — CoreClient
The ONLY way the bot talks to hypercode-core.
Bot sends intent → Core applies rules → Bot renders response.

Never touches Supabase directly. Never holds service-role key.
"""
import hashlib
import json
import os
import httpx
import discord
from typing import Any

CORE_URL     = os.getenv("HYPERCODE_API_URL", "http://localhost:8000")
BOT_API_KEY  = os.getenv("BOT_API_KEY", "")          # set in .env / secrets
TIMEOUT      = 8.0                                     # seconds


class CoreError(Exception):
    """Raised when Core returns a non-retryable error."""
    def __init__(self, code: str, message: str, retryable: bool = False):
        self.code      = code
        self.message   = message
        self.retryable = retryable
        super().__init__(message)


class CoreClient:
    """
    Shared async HTTP client for all cogs.
    Instantiate once in bot.py, pass to every cog via __init__.
    """

    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=CORE_URL,
            timeout=TIMEOUT,
            headers={
                "Authorization": f"Bearer {BOT_API_KEY}",
                "Content-Type":  "application/json",
            },
        )

    # ── One Door ──────────────────────────────────────────────
    async def action(
        self,
        action:         str,
        discord_ctx:    dict,          # {user_id, guild_id, channel_id, interaction_id}
        payload:        dict = None,
    ) -> dict:
        """
        POST /api/v1/discord/actions
        Returns the full Core response dict.
        Raises CoreError on 4xx/5xx.
        """
        body = {
            "action":  action,
            "discord": discord_ctx,
            "payload": payload or {},
        }
        idem_key = f"discord:{discord_ctx.get('interaction_id', 'noid')}"
        req_hash = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode()
        ).hexdigest()[:16]

        try:
            resp = await self._client.post(
                "/api/v1/discord/actions",
                json=body,
                headers={
                    "Idempotency-Key": idem_key,
                    "X-Request-Hash":  req_hash,
                },
            )
        except httpx.TimeoutException:
            raise CoreError("timeout", "Core is taking too long — try again in a sec!", retryable=True)
        except httpx.ConnectError:
            raise CoreError("unavailable", "Core is offline — back soon!", retryable=True)

        return self._handle(resp)

    # ── Read endpoints ───────────────────────────────────────
    async def get_balance(self, discord_id: str) -> dict:
        """GET /api/v1/broski/balance/{discord_id}"""
        try:
            resp = await self._client.get(f"/api/v1/broski/balance/{discord_id}")
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise CoreError("unavailable", "Core unavailable", retryable=True)
        return self._handle(resp)

    async def get_pulse(self) -> dict:
        """GET /api/v1/broski/pulse"""
        try:
            resp = await self._client.get("/api/v1/broski/pulse")
        except (httpx.TimeoutException, httpx.ConnectError):
            raise CoreError("unavailable", "Core unavailable", retryable=True)
        return self._handle(resp)

    async def health(self) -> dict:
        """GET /health"""
        resp = await self._client.get("/health")
        return self._handle(resp)

    # ── Internal ─────────────────────────────────────────────
    def _handle(self, resp: httpx.Response) -> dict:
        if resp.status_code == 409:
            # Idempotency hit — return cached result, not an error
            return resp.json()
        if resp.status_code == 200:
            return resp.json()
        try:
            body = resp.json()
            raise CoreError(
                code=body.get("code", str(resp.status_code)),
                message=body.get("message", "Something went wrong"),
                retryable=body.get("retryable", False),
            )
        except Exception:
            raise CoreError("unknown", f"Core returned {resp.status_code}", retryable=False)

    async def close(self):
        await self._client.aclose()


# ── Render helpers ────────────────────────────────────────────
def render_to_embed(render: dict) -> discord.Embed:
    """
    Maps Core's render payload → discord.Embed.
    Core controls ALL content. Bot just maps fields.

    render shape:
      { type: "embed", title, description, color, fields[], footer, thumbnail }
    """
    embed = discord.Embed(
        title       = render.get("title", ""),
        description = render.get("description", ""),
        colour      = int(render.get("color", "0x5865F2").replace("#", "0x"), 16),
    )
    for f in render.get("fields", []):
        embed.add_field(
            name   = f.get("name", ""),
            value  = f.get("value", ""),
            inline = f.get("inline", True),
        )
    if footer := render.get("footer"):
        embed.set_footer(text=footer)
    if thumb := render.get("thumbnail"):
        embed.set_thumbnail(url=thumb)
    return embed


def fallback_embed(error: CoreError) -> discord.Embed:
    """
    Safe fallback shown when Core is unavailable.
    Never shows raw error details to users.
    """
    if error.retryable:
        desc = f"⏳ {error.message}\nTry again in a moment!"
        colour = 0xFFA500
    else:
        desc = "Something went sideways — the team has been notified! 🔧"
        colour = 0xFF4444

    embed = discord.Embed(
        title="⚠️ Heads up!",
        description=desc,
        colour=colour,
    )
    embed.set_footer(text="BROski Bot • Core unavailable")
    return embed
