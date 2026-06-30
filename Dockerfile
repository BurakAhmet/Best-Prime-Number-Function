# Minimal image packaging is_prime for GitHub Container Registry (Packages).
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE is_prime.py ./
COPY tests ./tests

RUN pip install --no-cache-dir .

# Default: show help via CLI
ENTRYPOINT ["is-prime"]
CMD ["17"]
