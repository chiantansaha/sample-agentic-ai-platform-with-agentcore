# Multi-stage build for React frontend

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy workspace files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages ./packages

# Copy frontend app
COPY apps/frontend ./apps/frontend

# Install dependencies
RUN pnpm install --frozen-lockfile

# Build argument for environment mode
ARG BUILD_MODE=development

# Build frontend with specified mode
WORKDIR /app/apps/frontend
RUN pnpm build --mode $BUILD_MODE

# Stage 2: Production with Nginx
FROM nginx:alpine

# Create non-root user
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup \
    && chown -R appuser:appgroup /var/cache/nginx /var/log/nginx /etc/nginx/conf.d \
    && mkdir -p /tmp/nginx && chown -R appuser:appgroup /tmp/nginx

# Copy custom nginx config
COPY apps/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder
COPY --from=builder /app/apps/frontend/dist /usr/share/nginx/html
RUN chown -R appuser:appgroup /usr/share/nginx/html

USER appuser

EXPOSE 8080

CMD ["nginx", "-g", "daemon off; pid /tmp/nginx/nginx.pid;"]
