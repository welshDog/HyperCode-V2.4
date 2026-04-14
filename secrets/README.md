# 🔐 HyperCode V2.4 — Secrets Folder

This folder holds Docker secrets as plain `.txt` files.
**This entire folder is gitignored. NEVER commit real keys.**

## 📋 Files in this folder

| File | What goes in it | Where to get it |
|---|---|---|
| `stripe_secret_key.txt` | `sk_test_...` or `sk_live_...` | [Stripe Dashboard → API Keys](https://dashboard.stripe.com/apikeys) |
| `stripe_publishable_key.txt` | `pk_test_...` or `pk_live_...` | [Stripe Dashboard → API Keys](https://dashboard.stripe.com/apikeys) |
| `stripe_webhook_secret.txt` | `whsec_...` | [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks) |
| `postgres_password.txt` | Your Postgres password | Set by you during init |
| `discord_token.txt` | Your Discord bot token | Discord Developer Portal |
| `openai_api_key.txt` | `sk-...` | OpenAI Platform |
| `jwt_secret.txt` | Random 64-char string | Run: `openssl rand -hex 32` |

## 🚀 Quick Setup (PowerShell)

```powershell
# Run the setup script
.\scripts\setup-secrets.ps1
```

## 🚀 Quick Setup (Bash/WSL)

```bash
bash scripts/init-secrets.sh
```

## ⚠️ Golden Rules

- ✅ **DO** paste real keys into these `.txt` files on your local machine
- ✅ **DO** keep this folder in `.gitignore`
- 🔴 **NEVER** paste real keys in `.env` files you might accidentally commit
- 🔴 **NEVER** share these files in Discord, chat, or screenshots
- 🔴 **NEVER** push this folder to GitHub
