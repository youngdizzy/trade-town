# TradeTown Read-Only MCP Boundary 1.0 — isolated MCP service.
#
# Separate image on purpose: mcp 2.2.0 requires pydantic>=2.12.0 while the
# TradeTown backend pins pydantic==2.10.2 across ~15,700 lines of schema.
# These dependency sets must never share an environment.
FROM python:3.12-slim

WORKDIR /srv

RUN adduser --system --group --no-create-home mcp

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Owns only its own boundary database; no TradeTown volume is mounted.
RUN mkdir -p /data && chown -R mcp:mcp /data /srv
USER mcp

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/srv

EXPOSE 8090

CMD ["python", "-m", "app.server"]
