# Build context: repo root (needs ../assets and ../scripts alongside frontend/)

# ---- dev: hot-reloading Vite dev server, used by docker-compose.dev.yml ----
FROM node:22-alpine AS dev
WORKDIR /repo
COPY scripts ./scripts
COPY assets/cute-fantasy-rpg ./assets/cute-fantasy-rpg
COPY frontend/package*.json ./frontend/
WORKDIR /repo/frontend
RUN npm install
COPY frontend ./
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# ---- builder: production static build ----
FROM node:22-alpine AS builder
WORKDIR /repo
COPY scripts ./scripts
COPY assets/cute-fantasy-rpg ./assets/cute-fantasy-rpg
COPY frontend/package*.json ./frontend/
WORKDIR /repo/frontend
RUN npm ci
COPY frontend ./
RUN npm run build

# ---- runner: nginx serving the static build + reverse-proxying the backend ----
FROM nginx:1.27-alpine AS runner
COPY frontend/deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /repo/frontend/dist /usr/share/nginx/html
EXPOSE 80
