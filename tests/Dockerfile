FROM node:24-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install --global --ignore-scripts opencode-ai@1.18.35 \
    && node /usr/local/lib/node_modules/opencode-ai/postinstall.mjs
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /repo
CMD ["python3", "scripts/integration_test.py", "--native", "--report", "/results/linux-integration.json"]
