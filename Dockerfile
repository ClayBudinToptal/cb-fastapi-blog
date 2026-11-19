## Dockerfile
# BUILD STAGE

# pin exact Python version
FROM python:3.14.4-slim-bookworm AS builder

# Copy UV binary from official Docker image - pinned
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

# like cd /app - all files go in there
WORKDIR /app

# UV Docker optimizations
# pre-compile Python at build time
# copy files, don't use sym links (can cause problems)
# use Python from base image, do not download new
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

# Install dependencies first (cached if unchanged)
# copy files to ./ (current dir which is /app)
# install dependencies --locked == use exact versions in uv.lock
#  --no-install-project == install dependencies only, not project files
#  --no-dev == skip dev dependencies (pytest...)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev	

# Copy app code and install project
# Docker caches build steps by layer - install dependencies before code so code updates don't force dependency reloads
COPY . ./
RUN uv sync --locked --no-dev



# PRODUCTION STAGE
# start fresh from beginning all files gone unless explicitly copied
# FROM starts new stage, last is what goes into Image
FROM python:3.14.4-slim-bookworm

WORKDIR /app

# Run as non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Copy app and dependencies from builder stage
#  None of the other stuff from builder stage gets copied over - uv, caches, temp build files, etc. don't get copied
COPY --from=builder --chown=appuser:appuser /app /app

# add .venv path for deps
# Python output appears immediately (unbuffered)
# test port for local testing - Google Cloud Run will override this
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# command to run on startup
#  exec replaces shell so fastapi receives SIGTERM for clean shutdown
#  --host 0.0.0.0 listens on all network interfaces
#  --proxy-headers --forwarded-allow-ips  - get correct headers from requester (forwarded from load balancer, etc.)
# no workers - scales by starting more Docker instances
#
CMD ["/bin/sh", "-c", "exec fastapi run --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips '*'"]


