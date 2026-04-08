# 🚀 HyperStudio - Complete Setup Guide

**Your neurodivergent-first AI avatar platform for HyperCode tutorials!**

Built by BROski♾ for the Hyperfocus Zone community 💪

---

## 📦 What's Included

This complete codebase gives you:

✅ **Async Video Generator** - Create tutorial videos from text scripts  
✅ **Azure TTS Integration** - Welsh & English voices included  
✅ **Wav2Lip Lip Sync** - Industry-standard accuracy  
✅ **Supabase Backend** - Your existing database + storage  
✅ **FastAPI REST API** - Production-ready endpoints  
✅ **Docker Deployment** - One command to run  
✅ **Background Job Processing** - Non-blocking video generation  

---

## 🎯 Quick Start (This Weekend!)

### Prerequisites

**Hardware:**
- NVIDIA GPU (RTX 3060+ recommended, your 4080 is PERFECT!)
- 16GB RAM minimum
- 50GB free disk space

**Software:**
- Docker & Docker Compose
- Git
- NVIDIA Container Toolkit (for GPU support)

**Accounts:**
- Supabase project (you already have this!)
- Azure Speech Services (free tier: 500k characters/month)

---

## ⚡ Installation

### Step 1: Clone Repository

```bash
# Create project directory
mkdir -p ~/projects/hyperstudio
cd ~/projects/hyperstudio

# The files I'm creating go here!
```

### Step 2: Set Up Azure Speech Services

1. Go to [Azure Portal](https://portal.azure.com)
2. Create "Speech Services" resource
3. Select "Free F0" tier (0.5M characters/month FREE!)
4. Get your API key and region
5. Save for `.env` file

**Welsh Voice Options:**
- `cy-GB-NiaNeural` - Welsh female
- `cy-GB-AledNeural` - Welsh male

**English (British) Options:**
- `en-GB-RyanNeural` - British male (recommended!)
- `en-GB-SoniaNeural` - British female

### Step 3: Download Wav2Lip Model

```bash
# Create models directory
mkdir -p models

# Download Wav2Lip GAN model (best quality)
wget "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth" \
  -O models/wav2lip_gan.pth

# Download face detection model
mkdir -p models/face_detection
wget "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" \
  -O models/face_detection/s3fd.pth
```

### Step 4: Create Environment File

Create `.env` file:

```bash
# Azure Speech Services
AZURE_SPEECH_KEY=your_azure_key_here
AZURE_SPEECH_REGION=uksouth

# Supabase (from your existing project)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Application Settings
ENVIRONMENT=development
GPU_DEVICE=0
MAX_WORKERS=2
```

### Step 5: Prepare Avatar Images

Create `avatars/` directory with your BROski character:

```bash
mkdir -p avatars

# Add your avatar images:
# avatars/broski_default.png - Main avatar (512x512 or higher)
# avatars/broski_happy.png - Enthusiastic expression
# avatars/broski_focused.png - Serious teaching mode
# avatars/broski_thinking.png - Problem-solving face
```

**Quick Avatar Generation:**

Use Stable Diffusion or Midjourney with this prompt:

```
Professional AI assistant character, friendly young Welsh man, 
casual tech hoodie, warm genuine smile, approachable face, 
high quality portrait photo, neutral grey background, 
front-facing headshot, 4K resolution, soft studio lighting
```

Or hire a designer on Fiverr ($50-100) for custom character!

### Step 6: Run with Docker

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f hyperstudio-api

# Should see:
# ✓ Models loaded successfully
# ✓ GPU detected: NVIDIA GeForce RTX 4080
# ✓ Supabase connected
# ✓ Server running on http://0.0.0.0:8000
```

### Step 7: Test Your First Video!

```bash
# Test endpoint
curl -X POST "http://localhost:8000/v1/videos/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "avatar_id": "broski_default",
    "script": "Hey BRO! Welcome to HyperCode! Let me show you how neurodivergent programming works!",
    "voice_id": "en-GB-RyanNeural"
  }'

# Response:
# {
#   "video_id": "abc-123-def",
#   "status": "queued"
# }

# Check status
curl "http://localhost:8000/v1/videos/abc-123-def/status"

# When completed, video will be in Supabase Storage!
```

---

## 🏗️ Architecture

```
hyperstudio/
├── api/
│   ├── main.py              # FastAPI app & endpoints
│   ├── config.py            # Configuration management
│   └── dependencies.py      # Dependency injection
├── core/
│   ├── video_generator.py   # Wav2Lip video generation
│   ├── audio_processor.py   # Azure TTS integration
│   └── storage.py           # Supabase storage manager
├── models/                  # AI model weights
│   ├── wav2lip_gan.pth
│   └── face_detection/
├── avatars/                 # BROski character images
│   ├── broski_default.png
│   ├── broski_happy.png
│   └── broski_focused.png
├── docker-compose.yml       # Docker orchestration
├── Dockerfile              # Container image
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables
```

---

## 📊 Supabase Database Schema

Run this SQL in your Supabase SQL Editor:

```sql
-- Video generation jobs table
CREATE TABLE IF NOT EXISTS video_jobs (
    video_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    avatar_id TEXT NOT NULL,
    script TEXT NOT NULL,
    voice_id TEXT DEFAULT 'en-GB-RyanNeural',
    status TEXT CHECK (status IN ('queued', 'processing', 'completed', 'failed')) DEFAULT 'queued',
    video_url TEXT,
    thumbnail_url TEXT,
    error_message TEXT,
    duration_seconds FLOAT,
    processing_time_seconds FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Avatar library
CREATE TABLE IF NOT EXISTS avatars (
    avatar_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    image_url TEXT NOT NULL,
    is_custom BOOLEAN DEFAULT FALSE,
    user_id UUID REFERENCES auth.users(id),
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default BROski avatars
INSERT INTO avatars (avatar_id, name, description, image_url, tags) VALUES
('broski_default', 'BROski Default', 'Friendly main avatar for general tutorials', 'avatars/broski_default.png', ARRAY['default', 'friendly']),
('broski_happy', 'BROski Happy', 'Enthusiastic avatar for exciting concepts', 'avatars/broski_happy.png', ARRAY['excited', 'motivational']),
('broski_focused', 'BROski Focused', 'Serious teaching mode for complex topics', 'avatars/broski_focused.png', ARRAY['serious', 'technical']),
('broski_thinking', 'BROski Thinking', 'Problem-solving avatar for debugging', 'avatars/broski_thinking.png', ARRAY['thoughtful', 'analytical']);

-- Voice library
CREATE TABLE IF NOT EXISTS voices (
    voice_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    language TEXT NOT NULL,
    locale TEXT NOT NULL,
    gender TEXT,
    accent TEXT,
    description TEXT,
    preview_url TEXT,
    is_premium BOOLEAN DEFAULT FALSE
);

-- Insert available voices
INSERT INTO voices (voice_id, name, language, locale, gender, accent, description) VALUES
-- Welsh voices
('cy-GB-NiaNeural', 'Nia', 'Welsh', 'cy-GB', 'Female', 'Welsh', 'Native Welsh female voice'),
('cy-GB-AledNeural', 'Aled', 'Welsh', 'cy-GB', 'Male', 'Welsh', 'Native Welsh male voice'),
-- British English voices
('en-GB-RyanNeural', 'Ryan', 'English', 'en-GB', 'Male', 'British', 'British English male voice (recommended)'),
('en-GB-SoniaNeural', 'Sonia', 'English', 'en-GB', 'Female', 'British', 'British English female voice'),
('en-GB-LibbyNeural', 'Libby', 'English', 'en-GB', 'Female', 'British', 'Young British female voice'),
('en-GB-ThomasNeural', 'Thomas', 'English', 'en-GB', 'Male', 'British', 'Professional British male voice');

-- Usage analytics
CREATE TABLE IF NOT EXISTS avatar_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    video_id UUID REFERENCES video_jobs(video_id),
    action TEXT CHECK (action IN ('generate', 'view', 'download', 'share')),
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_jobs(status);
CREATE INDEX IF NOT EXISTS idx_video_jobs_user_id ON video_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_video_jobs_created_at ON video_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_avatar_usage_video_id ON avatar_usage(video_id);
CREATE INDEX IF NOT EXISTS idx_avatar_usage_timestamp ON avatar_usage(timestamp DESC);

-- Enable Row Level Security
ALTER TABLE video_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE avatars ENABLE ROW LEVEL SECURITY;
ALTER TABLE avatar_usage ENABLE ROW LEVEL SECURITY;

-- RLS Policies for video_jobs
CREATE POLICY "Users can view their own video jobs"
  ON video_jobs FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own video jobs"
  ON video_jobs FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- RLS Policies for avatars
CREATE POLICY "Public avatars are viewable by everyone"
  ON avatars FOR SELECT
  USING (is_custom = FALSE OR user_id = auth.uid());

CREATE POLICY "Users can create custom avatars"
  ON avatars FOR INSERT
  WITH CHECK (auth.uid() = user_id AND is_custom = TRUE);

-- RLS Policies for avatar_usage
CREATE POLICY "Users can view their own usage"
  ON avatar_usage FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can log their own usage"
  ON avatar_usage FOR INSERT
  WITH CHECK (auth.uid() = user_id);
```

---

## 🎨 Creating Your First Tutorial Video

### Example 1: Simple Introduction

```python
import requests

response = requests.post("http://localhost:8000/v1/videos/generate", json={
    "avatar_id": "broski_default",
    "script": """
        Hey BRO! Welcome to HyperCode!
        
        I'm BROski, your neurodivergent-first programming tutor.
        
        HyperCode is designed specifically for ADHD, dyslexic, 
        and autistic developers like us!
        
        Let's dive into how spatial programming works!
    """,
    "voice_id": "en-GB-RyanNeural"
})

video_id = response.json()["video_id"]
print(f"Video generating: {video_id}")
```

### Example 2: Welsh Language Tutorial

```python
response = requests.post("http://localhost:8000/v1/videos/generate", json={
    "avatar_id": "broski_focused",
    "script": """
        Helo BRO! Croeso i HyperCode!
        
        Rwy'n BROski, eich tiwtor rhaglennu niwroamrywiol gyntaf.
        
        Mae HyperCode wedi'i gynllunio'n arbennig ar gyfer 
        datblygwyr ADHD, dyslecsig, ac awtistig fel ni!
    """,
    "voice_id": "cy-GB-AledNeural"
})
```

### Example 3: Technical Deep-Dive

```python
response = requests.post("http://localhost:8000/v1/videos/generate", json={
    "avatar_id": "broski_focused",
    "script": """
        Right mate, let's break down how HyperCode's 
        spatial memory system works.
        
        Traditional code is linear - line by line, top to bottom.
        
        But neurodivergent brains often think in patterns, 
        networks, and spatial relationships.
        
        HyperCode lets you arrange code blocks spatially, 
        like organizing your desk the way YOUR brain works!
        
        No more forcing yourself into neurotypical linear thinking!
    """,
    "voice_id": "en-GB-RyanNeural"
})
```

---

## 🔧 Configuration Options

### Video Quality Settings

Edit `core/video_generator.py`:

```python
class VideoSettings:
    # Output video quality
    fps = 25  # Frames per second
    video_codec = 'libx264'  # H.264 encoding
    audio_codec = 'aac'  # AAC audio
    bitrate = '2000k'  # Video bitrate (higher = better quality)
    
    # Wav2Lip settings
    wav2lip_quality = 'Enhanced'  # 'Fast', 'Improved', 'Enhanced'
    face_detection_batch_size = 16
    wav2lip_batch_size = 128
```

### Voice Settings

Available Azure voices in `voices` table. Switch anytime!

**Tips:**
- `en-GB-RyanNeural` - Best for technical tutorials (clear, professional)
- `en-GB-LibbyNeural` - Younger, more energetic tone
- `cy-GB-AledNeural` - Welsh language, warm and friendly

---

## 💰 Cost Breakdown

### Free Tier (Perfect for MVP!)

| Service | Free Tier | Enough For |
|---------|-----------|------------|
| Azure TTS | 500k characters/month | ~100 tutorial videos |
| Supabase | 500MB storage | ~50 videos (10MB each) |
| Local GPU | $0 (your RTX 4080!) | Unlimited generation |
| **Total** | **$0/month** | **50-100 videos/month** |

### When You Scale Up

| Service | Cost | Usage |
|---------|------|-------|
| Azure TTS | $16/1M chars | ~200 videos |
| Supabase Pro | $25/month | 8GB storage (~800 videos) |
| Runpod GPU | $0.34/hour | On-demand processing |
| **Total** | **~$50/month** | **Production ready** |

---

## 🎯 Integration with HyperCode

### Auto-Generate Tutorials from Code

Add this to your HyperCode compiler:

```python
# In your HyperCode IDE
@hypercode_tutorial(auto_video=True)
def fibonacci(n: int) -> int:
    """
    Calculate Fibonacci sequence using HyperCode's 
    pattern-matching syntax.
    
    TUTORIAL: This function demonstrates HyperCode's 
    visual recursion patterns. Notice how the spatial 
    layout mirrors the mathematical relationship!
    """
    match n:
        case 0 | 1: return n
        case _: return fibonacci(n-1) + fibonacci(n-2)

# HyperStudio automatically creates tutorial video!
# Script extracted from docstring TUTORIAL section
```

### Discord Bot Integration

```python
# Discord command for Hyperfocus Zone
@bot.command()
async def tutorial(ctx, topic: str):
    """Generate HyperCode tutorial video on-demand"""
    
    # Get tutorial script from knowledge base
    script = get_tutorial_script(topic)
    
    # Generate video
    video_id = await hyperstudio.generate_video(
        avatar_id="broski_default",
        script=script,
        voice_id="en-GB-RyanNeural"
    )
    
    # Wait for completion (with progress updates)
    async with ctx.typing():
        video_url = await wait_for_video(video_id)
    
    # Send to Discord
    await ctx.send(f"Tutorial ready, BRO! {video_url}")
```

---

## 🚀 Next Steps

### Week 1: MVP Testing
- [ ] Generate 5 test videos with different avatars
- [ ] Test Welsh and English voices
- [ ] Share with Hyperfocus Zone community for feedback
- [ ] Measure GPU performance and generation times

### Week 2: HyperCode Integration
- [ ] Auto-generate tutorial for each HyperCode concept
- [ ] Create "BROski explains" series (50+ videos)
- [ ] Add video links to HyperCode documentation
- [ ] Discord bot for on-demand tutorials

### Week 3: Community Features
- [ ] Allow users to upload custom avatars
- [ ] Community avatar library
- [ ] Rate and review system
- [ ] Avatar marketplace (optional)

### Week 4: Production Deploy
- [ ] Deploy to Runpod for GPU acceleration
- [ ] Set up CDN for video delivery
- [ ] Add video analytics
- [ ] Launch publicly!

---

## 🐛 Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA driver
nvidia-smi

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Wav2Lip Model Not Loading

```bash
# Verify model file exists and is correct size
ls -lh models/wav2lip_gan.pth
# Should be ~197MB

# Re-download if needed
rm models/wav2lip_gan.pth
wget "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth" \
  -O models/wav2lip_gan.pth
```

### Azure TTS Errors

Check your `.env` file:
- `AZURE_SPEECH_KEY` - No quotes, just the key
- `AZURE_SPEECH_REGION` - Must match your Azure resource region (e.g., `uksouth`)

Test connection:
```bash
curl -X POST "https://uksouth.tts.speech.microsoft.com/cognitiveservices/v1" \
  -H "Ocp-Apim-Subscription-Key: YOUR_KEY" \
  -H "Content-Type: application/ssml+xml" \
  -d '<speak version="1.0" xml:lang="en-GB"><voice name="en-GB-RyanNeural">Test</voice></speak>'
```

### Video Generation Stuck

Check job status in Supabase:
```sql
SELECT * FROM video_jobs WHERE status = 'processing' ORDER BY created_at DESC;
```

Restart stuck jobs:
```sql
UPDATE video_jobs SET status = 'queued' WHERE status = 'processing' AND started_at < NOW() - INTERVAL '10 minutes';
```

---

## 📚 Resources

### Documentation
- [Wav2Lip Paper](https://arxiv.org/abs/2008.10010)
- [Azure TTS Documentation](https://learn.microsoft.com/azure/ai-services/speech-service/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Supabase Storage Guide](https://supabase.com/docs/guides/storage)

### Community
- [HyperCode GitHub](https://github.com/yourname/hypercode)
- [Hyperfocus Zone Discord](https://discord.gg/hyperfocus)
- [HyperStudio Discussions](https://github.com/yourname/hyperstudio/discussions)

---

## 💪 You Got This, BRO!

HyperStudio is YOUR platform. No subscriptions, no limits, no gatekeeping.

**What makes it special:**
- ✅ Built specifically for neurodivergent creators
- ✅ Welsh language support (representing!)
- ✅ Open source and hackable
- ✅ Runs on YOUR hardware
- ✅ Free tier covers serious usage
- ✅ Integrates perfectly with HyperCode

**The mission:** Make programming education accessible to EVERYONE, especially neurodivergent developers who've been left behind by traditional tools.

This is how we change the game! 🚀💓

---

**Ready to generate your first video? Let's GOOOO!** 🔥

Questions? Find me in the Hyperfocus Zone Discord! 

**— BROski♾ (aka your AI build partner)** 😎💪
