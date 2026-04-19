# 🧠 Runbook — Anthropic Credit Top-Up + Pet Chat Swap-Back

> **Goal:** restore Anthropic Claude (haiku/sonnet) as the primary LLM for `broski-pets-bridge`, replacing the Perplexity (sonar/sonar-pro) fallback that's been carrying chat since April 17, 2026.
> **Estimated time:** 2 minutes after the top-up clears.
> **Last updated:** April 19, 2026

---

## 0. The good news — no code or env change required

The pet chat code is already wired to **try Anthropic first, fall through to Perplexity automatically** on any non-200 response (including HTTP 402 credit-exhausted).

- Code: `agents/broski-pets-bridge/main.py:664` → `_chat_via_cloud()`
- Behaviour: Anthropic → Perplexity → Ollama (last-resort local)

So once credits land, **the next pet message uses Anthropic again**. No restart, no env flip, no deploy.

---

## 1. Top up Anthropic credits

1. Sign in: <https://console.anthropic.com/billing> as **lyndzwills@gmail.com**
2. **Plans & billing → Add credits** — minimum $5 is enough for ~3,000 pet chats with Haiku
3. Pay via card → wait ~30 seconds for the dashboard to show the new balance

> 💸 **Cost reference (April 2026 prices, give or take):**
> - Haiku 4.5 chat: ~$0.001 per pet message (~3,000 messages per $5)
> - Sonnet 4.6 ask:  ~$0.005 per pet message (~1,000 ask-mode messages per $5)
>
> Set a **monthly auto-recharge cap** in console.anthropic.com so you never get pinged again.

## 2. Verify credits landed

```bash
# From any terminal with the existing API key:
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","max_tokens":10,"messages":[{"role":"user","content":"ping"}]}' \
  | python -c "import sys, json; d = json.load(sys.stdin); print('OK' if 'content' in d else d)"
```

Expected output: `OK`. If you see a `credit_balance_too_low` error, top-up hasn't propagated yet — wait 60s.

## 3. Confirm pets are using Anthropic again

Send a test message to a pet via Discord (or the bot endpoint), then check the bridge log:

```bash
docker logs broski-pets-bridge --tail 50 | grep -E "model|claude|sonar"
```

Look for `claude-haiku-4-5-20251001` or `claude-sonnet-4-6` in the model field of the last reply. If you still see `sonar` / `sonar-pro`, Anthropic is still failing — re-run the curl in step 2 to diagnose.

## 4. (Optional) Lock in pinned model versions

If a new Claude family ships and you want pets to stay on a specific version until you've reviewed the change, pin them in `.env`:

```bash
PETS_ANTHROPIC_MODEL_CHAT=claude-haiku-4-5-20251001    # cheap, fast — for chat
PETS_ANTHROPIC_MODEL_ASK=claude-sonnet-4-6             # smarter — for ask mode (research, code review)
```

Then reload only the bridge (no downtime):

```bash
docker compose up -d --no-deps broski-pets-bridge
```

## 5. (Optional) Disable Perplexity fallback once you're confident

If you'd rather have pets fail loudly than silently degrade to Perplexity:

```bash
# In .env:
PERPLEXITY_API_KEY=         # blank disables Perplexity branch entirely
```

Trade-off: Anthropic outage → pets respond from local Ollama (slower, lower quality) instead of Perplexity. Keep Perplexity wired for resilience unless you have a strong reason.

## 6. Update `CLAUDE.md` after success

In `## 🏆 Achievements Unlocked` flip the existing line:

```diff
- ✅ **Pet chat via cloud LLM** — Anthropic (haiku/sonnet) → Perplexity fallback (sonar/sonar-pro). 3.8s chat, 12.7s ask. CPU Ollama retired from chat path. (April 17)
+ ✅ **Pet chat via cloud LLM** — Anthropic restored as primary (haiku/sonnet); Perplexity (sonar/sonar-pro) on standby fallback. 3.8s chat, 12.7s ask. (<date>)
```

In the "For New Claude Sessions" section, remove the line about Anthropic credits needing top-up.

---

## 🆘 If pets are slow after the swap-back

Anthropic API latency varies by region and model load. Sanity check:

```bash
time curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","max_tokens":80,"messages":[{"role":"user","content":"Say hi in 5 words"}]}' \
  > /dev/null
```

Expected: < 2s end-to-end. If consistently > 5s, switch the chat model to a closer-region or smaller variant in `.env` and re-up the bridge.
