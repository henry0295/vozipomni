# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files (.npmrc activa legacy-peer-deps)
COPY package*.json .npmrc ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

# Nuxt/Nitro genera un servidor autocontenido en .output (incluye sus
# propios node_modules), así que no hace falta reinstalar dependencias aquí.
# Un "npm install --omit=dev" sin lockfile fallaba con
# "Cannot read properties of null (reading 'edgesOut')" y además
# ejecutaba el postinstall "nuxt prepare" sin el código fuente.

# Copy built application from builder
COPY --from=builder /app/.output /app/.output

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV NUXT_HOST=0.0.0.0
ENV NUXT_PORT=3000

# Start the application
CMD ["node", ".output/server/index.mjs"]
