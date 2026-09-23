# Multi-stage: build the Vite app with Node, then serve the static output
# with nginx. Nobody running this container needs Node installed at all.

FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Baked in at build time -- Vite inlines env vars starting with VITE_ into
# the JS bundle, so this has to be a build ARG, not a runtime ENV.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
