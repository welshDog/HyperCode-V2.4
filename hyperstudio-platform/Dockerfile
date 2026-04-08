# HyperStudio Docker Image
# Neurodivergent-first avatar video generation platform
# Built with PyTorch + CUDA for GPU acceleration

FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Set working directory
WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Copy application code
COPY api/ ./api/
COPY core/ ./core/

# Create necessary directories
RUN mkdir -p /app/models /app/avatars /tmp/hyperstudio

# Download Wav2Lip model (optional - can be mounted as volume)
# Uncomment to bake model into image (increases image size by ~200MB)
# RUN wget -q "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth" \
#     -O /app/models/wav2lip_gan.pth

# Download face detection model
RUN mkdir -p /app/models/face_detection && \
    wget -q "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" \
    -O /app/models/face_detection/s3fd.pth

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/')"

# Run FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
