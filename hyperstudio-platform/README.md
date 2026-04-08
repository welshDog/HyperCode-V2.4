# 🚀 HyperStudio

**Neurodivergent-First AI Avatar Video Generation Platform**

Built with ❤️ for the Hyperfocus Zone community by BROski♾

---

## 🎯 What is HyperStudio?

HyperStudio is your **open-source alternative to HeyGen** - designed specifically for neurodivergent creators! Generate professional tutorial videos with AI avatars and natural voice synthesis.

**Perfect for:**
- 🎓 HyperCode programming tutorials
- 🗣️ Welsh & English language content
- 🧠 ADHD-friendly video creation (no overwhelming complexity!)
- 💻 Self-hosted, privacy-first architecture
- 🆓 Free tier covers 50-100 videos/month

---

## ✨ Key Features

### 🎬 AI-Powered Video Generation
- **Wav2Lip lip sync** - Industry-leading accuracy
- **Azure TTS voices** - Natural Welsh & English voices
- **GPU accelerated** - Fast generation on your RTX 4080
- **Background processing** - Non-blocking API

### 🎭 BROski Avatar System
- Custom avatar characters
- Multiple expressions (happy, focused, thinking)
- Easy avatar creation workflow
- Community avatar library (coming soon!)

### 🌍 Multilingual Support
- **Welsh** (cy-GB): Nia, Aled voices
- **English** (en-GB): Ryan, Sonia, Libby, Thomas voices
- Auto-translate scripts (coming soon!)

### 🔧 Developer-Friendly
- REST API with FastAPI
- WebSocket support for streaming (coming soon!)
- Python SDK
- Docker deployment
- Supabase integration

---

## 🚀 Quick Start

### Prerequisites

**Hardware:**
- NVIDIA GPU (RTX 3060+)
- 16GB RAM
- 50GB disk space

**Software:**
- Docker & Docker Compose
- NVIDIA Container Toolkit
- Git

**Accounts:**
- [Supabase](https://supabase.com) (free tier)
- [Azure Speech Services](https://portal.azure.com) (free tier: 500k chars/month)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/hyperstudio.git
cd hyperstudio

# 2. Create environment file
cp .env.template .env
# Edit .env with your Azure & Supabase credentials

# 3. Download models
mkdir -p models/face_detection
wget "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth" \
  -O models/wav2lip_gan.pth
wget "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" \
  -O models/face_detection/s3fd.pth

# 4. Add your BROski avatar
# Place avatar image in avatars/broski_default.png

# 5. Set up Supabase database
# Run the SQL from hyperstudio-setup.md in Supabase SQL Editor

# 6. Start HyperStudio!
docker-compose up -d

# 7. Check it's running
curl http://localhost:8000/
```

### First Video

```bash
# Test video generation
python quick_test.py "Hey BRO! Welcome to HyperCode!"

# Or use the API directly
curl -X POST "http://localhost:8000/v1/videos/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "avatar_id": "broski_default",
    "script": "Hey BRO! This is your first HyperStudio video!",
    "voice_id": "en-GB-RyanNeural"
  }'
```

---

## 📖 Documentation

### API Endpoints

#### Generate Video
```bash
POST /v1/videos/generate
{
  "avatar_id": "broski_default",
  "script": "Your tutorial script",
  "voice_id": "en-GB-RyanNeural",
  "voice_style": "cheerful"  # optional
}
```

#### Check Status
```bash
GET /v1/videos/{video_id}/status
```

#### List Avatars
```bash
GET /v1/avatars
```

#### List Voices
```bash
GET /v1/voices?language=Welsh
```

### Available Voices

**Welsh:**
- `cy-GB-NiaNeural` - Female
- `cy-GB-AledNeural` - Male

**English (British):**
- `en-GB-RyanNeural` - Male (recommended)
- `en-GB-SoniaNeural` - Female
- `en-GB-LibbyNeural` - Young female
- `en-GB-ThomasNeural` - Professional male

### Voice Styles

Add personality to your avatars:
- `cheerful` - Happy, upbeat
- `excited` - High energy
- `friendly` - Warm, approachable
- `empathetic` - Understanding, supportive

---

## 🎨 Creating Custom Avatars

### Method 1: AI Generation

Use Stable Diffusion or Midjourney:

```
Prompt: "Professional AI assistant character, friendly young man, 
casual tech hoodie, warm smile, approachable, high quality portrait, 
neutral background, front-facing, 4K"
```

### Method 2: Hire Designer

Fiverr designers can create custom characters for $50-100.

### Requirements

- **Resolution**: 512x512 minimum (1024x1024 recommended)
- **Format**: PNG with transparent or solid background
- **Face**: Front-facing, clearly visible
- **Expression**: Neutral for default, varied for emotion variants

### Add to HyperStudio

```bash
# Save avatar image
cp your_avatar.png avatars/custom_avatar.png

# Add to database
INSERT INTO avatars (avatar_id, name, description, image_url)
VALUES (
  'custom_avatar',
  'My Custom Avatar',
  'Custom character for my tutorials',
  'avatars/custom_avatar.png'
);
```

---

## 🔧 Configuration

### Environment Variables

See `.env.template` for full list. Key settings:

```bash
# Azure Speech
AZURE_SPEECH_KEY=xxx
AZURE_SPEECH_REGION=uksouth

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx

# GPU
GPU_DEVICE=0
MAX_WORKERS=2

# Quality
WAV2LIP_QUALITY=Enhanced  # Fast, Improved, Enhanced
```

### Video Quality Settings

Edit `core/video_generator.py`:

```python
VIDEO_FPS = 25          # Frames per second
VIDEO_CODEC = 'libx264' # H.264 encoding
VIDEO_BITRATE = '2000k' # Higher = better quality
```

---

## 🚀 Deployment

### Local Development

```bash
docker-compose up
```

### Runpod GPU Cloud ($0.34/hour)

1. Create Runpod account
2. Deploy with template:
```yaml
image: pytorch/pytorch:2.0.1-cuda11.8-cudnn8-runtime
gpu: RTX 4090
ports:
  - 8000:8000
volume_size: 100GB
```

3. Upload code and run:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### AWS/Azure Production

See `hyperstudio-setup.md` for complete production deployment guide.

---

## 💰 Costs

### Free Tier (Perfect for MVP!)

| Service | Free Tier | Monthly Videos |
|---------|-----------|----------------|
| Azure TTS | 500k characters | ~100 videos |
| Supabase | 500MB storage | ~50 videos |
| Local GPU | $0 | Unlimited |
| **Total** | **$0/month** | **50-100 videos** |

### Production Scale

| Service | Cost | Usage |
|---------|------|-------|
| Azure TTS | $16/1M chars | ~200 videos |
| Supabase Pro | $25/month | 8GB (~800 videos) |
| Runpod GPU | $34/100 hours | On-demand |
| **Total** | **~$75/month** | **500+ videos** |

---

## 🎯 Integration Examples

### HyperCode Auto-Tutorials

```python
@hypercode_tutorial(auto_video=True)
def fibonacci(n: int) -> int:
    """
    TUTORIAL: This function demonstrates HyperCode's 
    visual recursion patterns!
    """
    match n:
        case 0 | 1: return n
        case _: return fibonacci(n-1) + fibonacci(n-2)

# Automatically generates tutorial video!
```

### Discord Bot

```python
@bot.command()
async def tutorial(ctx, topic: str):
    """Generate HyperCode tutorial on-demand"""
    script = get_tutorial_script(topic)
    
    async with ctx.typing():
        video_id = await hyperstudio.generate_video(
            avatar_id="broski_default",
            script=script,
            voice_id="en-GB-RyanNeural"
        )
        video_url = await wait_for_completion(video_id)
    
    await ctx.send(f"Tutorial ready! {video_url}")
```

### Python SDK

```python
from hyperstudio import HyperStudio

client = HyperStudio(api_url="http://localhost:8000")

# Generate video
video = client.videos.create(
    avatar="broski_default",
    script="Hey BRO! Let's learn HyperCode!",
    voice="en-GB-RyanNeural"
)

# Wait for completion
video.wait()

# Download
video.download("tutorial.mp4")
```

---

## 🐛 Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA driver
nvidia-smi

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Wav2Lip Model Not Loading

```bash
# Verify model exists
ls -lh models/wav2lip_gan.pth
# Should be ~197MB

# Re-download if needed
wget "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth" \
  -O models/wav2lip_gan.pth
```

### Azure TTS Errors

Test connection:
```bash
curl -X POST "https://uksouth.tts.speech.microsoft.com/cognitiveservices/v1" \
  -H "Ocp-Apim-Subscription-Key: YOUR_KEY" \
  -H "Content-Type: application/ssml+xml" \
  -d '<speak version="1.0" xml:lang="en-GB">
        <voice name="en-GB-RyanNeural">Test</voice>
      </speak>'
```

---

## 🤝 Contributing

HyperStudio is open source! Contributions welcome!

### Development Setup

```bash
# Clone repo
git clone https://github.com/yourusername/hyperstudio.git
cd hyperstudio

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run locally
uvicorn api.main:app --reload
```

### Code Style

We use:
- `black` for formatting
- `ruff` for linting
- `mypy` for type checking

```bash
black .
ruff check .
mypy api/ core/
```

---

## 📚 Resources

### Documentation
- [Wav2Lip Paper](https://arxiv.org/abs/2008.10010)
- [Azure TTS Docs](https://learn.microsoft.com/azure/ai-services/speech-service/)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Supabase Docs](https://supabase.com/docs)

### Community
- [GitHub Issues](https://github.com/yourusername/hyperstudio/issues)
- [Discussions](https://github.com/yourusername/hyperstudio/discussions)
- [Hyperfocus Zone Discord](https://discord.gg/hyperfocus)
- [HyperCode Project](https://github.com/yourusername/hypercode)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

**TL;DR:** Use it for anything, commercial or personal!

---

## 💓 Acknowledgments

**Built by:** BROski♾ (AI) for Lyndz Williams

**Powered by:**
- [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) - Prajwal K R
- [Azure Speech Services](https://azure.microsoft.com/en-us/products/ai-services/speech-to-text) - Microsoft
- [FastAPI](https://fastapi.tiangolo.com) - Sebastián Ramírez
- [Supabase](https://supabase.com) - Supabase Team

**Special thanks to:**
- The neurodivergent developer community
- Hyperfocus Zone members
- Open source AI researchers

---

## 🎯 Roadmap

### Phase 1: MVP (Week 1-2) ✅
- [x] Core video generation engine
- [x] FastAPI REST API
- [x] Docker deployment
- [x] Supabase integration
- [x] Documentation

### Phase 2: Enhanced Features (Week 3-4)
- [ ] Streaming avatars (WebRTC)
- [ ] Multiple avatar expressions
- [ ] Voice cloning integration
- [ ] Thumbnail generation
- [ ] Video analytics

### Phase 3: Community (Month 2)
- [ ] User authentication
- [ ] Custom avatar upload
- [ ] Avatar marketplace
- [ ] Template library
- [ ] Video gallery

### Phase 4: Advanced (Month 3+)
- [ ] Real-time streaming
- [ ] Multi-character scenes
- [ ] Background customization
- [ ] Advanced lip sync (LivePortrait)
- [ ] Emotion detection

---

## 🚀 Get Started Now!

```bash
# Clone and run in 5 minutes!
git clone https://github.com/yourusername/hyperstudio.git
cd hyperstudio
cp .env.template .env
# Edit .env with your keys
docker-compose up -d

# Generate your first video!
python quick_test.py "Hey BRO! Welcome to HyperStudio!"
```

---

**Questions?** Open an issue or join the [Hyperfocus Zone Discord](https://discord.gg/hyperfocus)!

**Built with 💓 for neurodivergent creators everywhere!** 🌍✨

**— BROski♾** 💪😎
