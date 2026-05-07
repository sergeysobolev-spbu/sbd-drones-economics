# Multi-stage: production Nitro server (nuxt dev breaks behind reverse proxy — Vite IPC).
FROM node:22-slim AS builder
WORKDIR /app
COPY systems/uas_dev_company/web/package.json /app/package.json
RUN npm install
COPY systems/uas_dev_company/web /app
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
COPY --from=builder /app/.output /app/.output
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
