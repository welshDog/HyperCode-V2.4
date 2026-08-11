# Multi-purpose builder image for HyperCode project
# This image can be used for builds, tests, and CI/CD pipelines

ARG NODE_IMAGE=node:20.18.1-bookworm-slim
FROM ${NODE_IMAGE} as node

FROM python:3.14-slim-bookworm as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js without curl|bash (copy from official node image)
# Supply-chain note: pin NODE_IMAGE (ideally with a digest) in CI/build args for reproducibility.
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/bin/npm /usr/local/bin/npm
COPY --from=node /usr/local/bin/npx /usr/local/bin/npx
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules

# Install common Python tools
RUN pip install --no-cache-dir \
    pip-tools \
    wheel \
    setuptools \
    twine

WORKDIR /workspace

# ==================== Development Stage ====================
FROM base as development

# Install development tools
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-asyncio \
    pytest-mock \
    black \
    ruff \
    mypy \
    ipython \
    debugpy \
    pre-commit

CMD ["/bin/bash"]

# ==================== Testing Stage ====================
FROM development as testing

# Install additional test dependencies
RUN pip install --no-cache-dir \
    faker \
    factory-boy \
    hypothesis \
    responses \
    freezegun \
    pytest-xdist \
    pytest-timeout

# Install performance testing tools
RUN npm install -g artillery

WORKDIR /tests

CMD ["pytest", "-v"]

# ==================== CI Stage ====================
FROM development as ci

# Install CI/CD specific tools
RUN pip install --no-cache-dir \
    coverage[toml] \
    pytest-html \
    pytest-json-report \
    bandit \
    safety

# Install code quality tools
RUN npm install -g \
    eslint \
    prettier \
    @commitlint/cli

WORKDIR /ci

CMD ["/bin/bash"]

# ==================== Documentation Builder ====================
FROM base as docs

# Install documentation tools
RUN pip install --no-cache-dir \
    mkdocs \
    mkdocs-material \
    mkdocstrings[python] \
    mkdocs-gen-files \
    mkdocs-literate-nav \
    mkdocs-section-index

WORKDIR /docs

CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8000"]

# ==================== Database Migration ====================
FROM base as migration

# Install Prisma and migration tools
RUN pip install --no-cache-dir \
    prisma \
    alembic \
    sqlalchemy

WORKDIR /migrations

CMD ["prisma", "migrate", "deploy"]
