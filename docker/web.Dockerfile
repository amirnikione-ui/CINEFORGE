# CINEFORGE web studio (Next.js) — multi-stage build.
#
# NOTE: we deliberately do NOT assume `output: 'standalone'` in apps/web/next.config.mjs
# (that file is owned by the web agent and may or may not set it). The runner stage
# therefore copies the whole built app + node_modules and serves with `npm run start`.
# If standalone lands later, shrink this stage to `.next/standalone` + `.next/static`.
FROM node:20-alpine AS deps
WORKDIR /app
# Manifests only first, so the npm layer caches across code changes.
COPY apps/web/package.json apps/web/package-lock.json* ./
# `npm ci` needs a lockfile; apps/web may not have committed one yet.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
COPY --from=builder /app ./

# Non-root runtime (consistent with the api/worker images).
RUN addgroup -g 1000 -S cineforge \
    && adduser -u 1000 -S cineforge -G cineforge \
    && mkdir -p /data \
    && chown -R cineforge:cineforge /data /app
USER cineforge

EXPOSE 3000
CMD ["npm", "run", "start"]
