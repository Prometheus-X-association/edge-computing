# Use the official Node.js alpine image as base image
FROM node:22-alpine
ARG ENV
ENV ENV=$ENV
# Install pnpm globally & Create app directory
WORKDIR /usr/src/app
RUN npm install -g pnpm@9.15.5 && apk add --no-cache gettext-envsubst git
# Bundle app source
COPY ./ ./
# Install app dependencies
RUN mkdir -p ./src/keys ./docs ./src/public/uploads && pnpm install --frozen-lockfile --ignore-scripts
# Build resources
RUN npm run build
# Copy init script
COPY ./scripts/entrypoint.pdc.sh ./entrypoint.sh
# Expose the port on which the app will run
EXPOSE 3000
CMD ["/bin/sh", "entrypoint.sh"]
