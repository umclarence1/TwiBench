# TwiBench on Hugging Face Spaces (Docker SDK, free CPU tier: 2 vCPU / 16 GB RAM).

# --- 1. Build the React front end -----------------------------------------
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# --- 2. Python server + model ---------------------------------------------
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Spaces run as user 1000
RUN useradd -m -u 1000 user
ENV HOME=/home/user HF_HOME=/home/user/.cache/huggingface PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
WORKDIR /home/user/app

COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY --chown=user src/ src/
COPY --chown=user server/ server/
COPY --chown=user results/ results/
COPY --chown=user data/ data/
COPY --from=web --chown=user /web/dist web/dist
USER user

# The fine-tuned model is downloaded from the Hub on first use (set in the Space settings or below).
ARG TWIBENCH_MODEL
ENV TWIBENCH_MODEL=${TWIBENCH_MODEL} TWIBENCH_HOST=0.0.0.0 TWIBENCH_PORT=7860 TWIBENCH_OPEN=0
EXPOSE 7860
CMD ["python", "server/app.py"]
