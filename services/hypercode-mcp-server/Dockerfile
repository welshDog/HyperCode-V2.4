FROM python:3.11-slim

WORKDIR /app

# Pip tool hardening - setuptools>=80 vendors patched jaraco.context; wheel 0.46.2 fixes CVE-2026-24049
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Fail the build here, not at runtime, if the MCP SDK pin ever drifts to v2
# (v2 drops the v1 API surface server.py imports).
RUN python -c "from mcp.server.fastmcp import FastMCP; FastMCP('build-check').sse_app()"

COPY server.py .

# Run as non-root (uid 1000), same pattern as agents/*
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8823

CMD ["python", "server.py"]
