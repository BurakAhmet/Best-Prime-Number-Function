# Minimal image packaging is_prime for GitHub Container Registry (Packages).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends gcc libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE MANIFEST.in is_prime.py ./
COPY is_prime_data ./is_prime_data
COPY tests ./tests
COPY scripts ./scripts
COPY benchmarks ./benchmarks

RUN bash scripts/compile_wheel_core.sh || true \
    && pip install --no-cache-dir .

# Default: show help via CLI
ENTRYPOINT ["is-prime"]
CMD ["17"]
