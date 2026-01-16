FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gzip && \
    rm -rf /var/lib/apt/lists/*

RUN curl -L https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz \
    -o rockyou.txt.tar.gz && \
    tar -xzf rockyou.txt.tar.gz && \
    rm rockyou.txt.tar.gz

COPY pyproject.toml uv.lock ./
RUN uv pip install -r pyproject.toml --system --compile-bytecode

FROM python:3.14-slim
COPY --from=builder /usr/local /usr/local

WORKDIR /app
COPY --from=builder ./rockyou.txt ./rockyou.txt
COPY app.py app.py

EXPOSE 8080
CMD ["python3", "app.py", "--disable-openapi", "--fast", "--workers", "1", "--processes", "1"]
