import pytest
from unittest.mock import AsyncMock, MagicMock

from src.cogs.briefing import MorningBriefing


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    return bot


@pytest.fixture
def briefing_cog(mock_bot):
    return MorningBriefing(mock_bot)


@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.user.id = 123456789
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.mark.asyncio
async def test_briefing_sends_embed(briefing_cog, mock_interaction, monkeypatch):
    async def fake_fetch(url: str):
        if url.endswith("/health"):
            return {"status": "ok"}
        if "/api/v1/broski/balance/" in url:
            return {"coins": 4242, "daily_claimed": True}
        return None

    monkeypatch.setattr(briefing_cog, "_fetch_json", fake_fetch)
    monkeypatch.setattr("src.cogs.briefing._read_next_up_from_whats_done", lambda _: "B3 verify")
    monkeypatch.setattr("src.cogs.briefing._get_last_commit_line", lambda _: "abc123 feat: ship it")
    monkeypatch.setattr("src.cogs.briefing.settings.workspace_path", ".")

    await briefing_cog.briefing.callback(briefing_cog, mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    _, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs["embed"]
    assert "Morning Briefing" in embed.title
    fields = {f.name: f.value for f in embed.fields}
    assert fields["Stack"] == "✅ All up"
    assert "4,242" in fields["BROski$"]
    assert fields["Next Task"] == "B3 verify"
    assert "abc123" in fields["Last Commit"]
