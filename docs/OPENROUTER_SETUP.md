# OpenRouter Integration Guide

## Overview

HyperCode now supports **OpenRouter** as an LLM provider, giving you access to 200+ models including **free tier** models for unlimited inference without credit burn.

## Quick Start

### 1. Get your API key

1. Visit [openrouter.ai](https://openrouter.ai)
2. Sign up / log in
3. Go to **API Keys**
4. Copy your key (starts with `sk-or-v1-`)

### 2. Configure HyperCode

Add to your `.env` file:

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_DEFAULT_MODEL=mistralai/mistral-7b-instruct:free
```

### 3. Use in code

```python
from app.core.model_routes import route_model_request

async for chunk in route_model_request(
    provider="openrouter",
    model="mistralai/mistral-7b-instruct:free",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.7,
    max_tokens=2048,
    stream=True,
    api_key=os.getenv("OPENROUTER_API_KEY"),
):
    print(chunk)
```

## Free Models

These models are **completely free** (no credits required):

| Model | Provider | Context | Best For |
|-------|----------|---------|----------|
| `mistralai/mistral-7b-instruct:free` | Mistral AI | 8K | General chat, code |
| `google/gemma-7b-it:free` | Google | 8K | Creative writing |
| `meta-llama/llama-3-8b-instruct:free` | Meta | 8K | Reasoning, Q&A |
| `openchat/openchat-7b:free` | OpenChat | 8K | Multi-turn dialogue |

## Paid Models (cheap)

OpenRouter also provides pay-per-use access to premium models:

- `anthropic/claude-3-5-sonnet` — ~$0.03/1K tokens
- `openai/gpt-4o-mini` — ~$0.015/1K tokens
- `google/gemini-pro-1.5` — ~$0.007/1K tokens

## Testing

Run a quick test:

```bash
cd backend
python -c "
import asyncio
import os
from app.llm.openrouter import chat_completion

async def test():
    async for chunk in chat_completion(
        model='mistralai/mistral-7b-instruct:free',
        messages=[{'role': 'user', 'content': 'Say hello!'}],
        api_key=os.getenv('OPENROUTER_API_KEY')
    ):
        if 'choices' in chunk:
            delta = chunk['choices'][0].get('delta', {})
            if 'content' in delta:
                print(delta['content'], end='', flush=True)

asyncio.run(test())
"
```

## IDE Integration

To use OpenRouter in the HyperCode IDE:

1. Set `OPENROUTER_DEFAULT_MODEL` to your preferred free model
2. The IDE will automatically use OpenRouter when no other provider is specified
3. Unlimited runs — no credit burn!

## Troubleshooting

**401 Unauthorized**
- Check your `OPENROUTER_API_KEY` is correct
- Ensure no extra spaces in `.env`

**429 Rate Limited**
- Free models have rate limits
- Try a different free model or add a small credit balance

**Model not found**
- Check the model identifier on [openrouter.ai/models](https://openrouter.ai/models)
- Some models require credits; append `:free` for free tier

## Resources

- [OpenRouter Docs](https://openrouter.ai/docs)
- [Model List](https://openrouter.ai/models)
- [Pricing](https://openrouter.ai/pricing)

---

**Nice one BROski♾️** — unlimited free AI runs for HyperCode!
