# syntax=docker/dockerfile:1
#
# AETHON container image — headless web UI + dashboard + webhook + messaging bots.
# Build:  docker build -t aethon .
# Run:    docker run -p 18790:18790 -e OPENAI_API_KEY=sk-... aethon
#         (bring your own model provider — set an API key, point at any OpenAI-compatible
#          base URL, or run local Ollama — see docker/config.docker.yaml)

############################
# Builder
############################
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Optional extras to bundle into the image, e.g. --build-arg EXTRAS=ollama
ARG EXTRAS=""

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /src
# Files the build backend (hatchling) needs: metadata, README, license, and the package.
COPY pyproject.toml README.md LICENSE ./
COPY aethon ./aethon

RUN pip install --upgrade pip \
    && if [ -n "$EXTRAS" ]; then pip install ".[$EXTRAS]"; else pip install .; fi

############################
# Runtime
############################
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Run as a non-root user.
RUN useradd --create-home --uid 10001 aethon

COPY --from=builder /opt/venv /opt/venv

# Seed a headless default config. Only used when the state volume is empty;
# a mounted config/volume takes precedence.
COPY docker/config.docker.yaml /home/aethon/.aethon/config.yaml
RUN chown -R aethon:aethon /home/aethon/.aethon

USER aethon
WORKDIR /home/aethon

EXPOSE 18790
VOLUME ["/home/aethon/.aethon"]

# Liveness: the web server answers /health on loopback inside the container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:18790/health', timeout=4)" || exit 1

CMD ["aethon", "start"]
