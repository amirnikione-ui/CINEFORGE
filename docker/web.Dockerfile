# CINEFORGE web studio — Next.js 14 (agent-02 VEGA's apps/web).
# Uses the committed package-lock for reproducible installs. CF-018.
FROM node:20-alpine AS build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./apps/web/
RUN cd apps/web && npm ci --no-audit --no-fund
COPY apps/web ./apps/web
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN cd apps/web && npm run build

FROM node:20-alpine
WORKDIR /app/apps/web
COPY --from=build /app/apps/web ./
ENV NODE_ENV=production
EXPOSE 3000
CMD ["npm", "run", "start"]
