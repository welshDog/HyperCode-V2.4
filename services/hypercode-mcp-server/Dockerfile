FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Fail the build here, not at runtime, if the MCP SDK pin ever drifts to v2
# (v2 drops the v1 API surface server.py imports).
RUN python -c "from mcp.server.fastmcp import FastMCP; FastMCP('build-check').sse_app()"

COPY server.py .

EXPOSE 8823

CMD ["python", "server.py"]
