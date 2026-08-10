# Minimal image packaging best_prime for GitHub Container Registry (Packages).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends gcc libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml setup.py README.md LICENSE MANIFEST.in ./
COPY best_prime ./best_prime
COPY is_prime_data ./is_prime_data
COPY scripts ./scripts

RUN bash scripts/compile_wheel_core.sh \
    && test -f is_prime_data/wheel_core.so \
    && pip install --no-cache-dir .

ENTRYPOINT ["is-prime"]
CMD ["17"]
