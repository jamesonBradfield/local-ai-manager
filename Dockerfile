# Multi-stage build for Local AI Manager
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Build llama.cpp
RUN git clone https://github.com/ggerganov/llama.cpp.git /llama.cpp \
    && cd /llama.cpp \
    && cmake -B build -DLLAMA_CUDA=OFF -DLLAMA_VULKAN=OFF \
    && cmake --build build --config Release -j$(nproc)

# Copy Local AI Manager
COPY . /build/

# Install Python dependencies
RUN pip install --no-cache-dir --user -e .

# Production image
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -u 1000 localai

# Copy llama.cpp binaries
COPY --from=builder /llama.cpp/build/bin/llama-server /usr/local/bin/
COPY --from=builder /llama.cpp/build/bin/llama-cli /usr/local/bin/

# Copy Local AI Manager
COPY --from=builder /root/.local /home/localai/.local
COPY --from=builder /build /app

# Set up directories
RUN mkdir -p /home/localai/models /home/localai/.config/local-ai /home/localai/.cache/local-ai \
    && chown -R localai:localai /home/localai /app

USER localai
WORKDIR /home/localai

# Add local bin to PATH
ENV PATH=/home/localai/.local/bin:$PATH
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["local-ai", "start", "--background"]

# Labels
LABEL org.opencontainers.image.title="Local AI Manager"
LABEL org.opencontainers.image.description="Extensible local AI management system"
LABEL org.opencontainers.image.version="2.0.0"
