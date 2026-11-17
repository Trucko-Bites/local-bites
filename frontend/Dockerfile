# Production image for the frontend.
# Stage 1 builds the React app; stage 2 serves it with Caddy, which also
# reverse-proxies /api and /admin to Django and handles HTTPS certificates.

# ---- Stage 1: build ----
FROM node:22-alpine AS build
WORKDIR /app

# Install dependencies first so this layer is cached between code changes
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite bakes VITE_* variables into the bundle at build time
ARG VITE_TILE_URL=""
ENV VITE_TILE_URL=${VITE_TILE_URL}
RUN npm run build

# ---- Stage 2: serve ----
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
