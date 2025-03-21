# Use the official Node.js alpine image as base image
FROM node:23.9.0-alpine
ARG ENV
ENV ENV=$ENV
# Install pnpm globally & Create app directory
WORKDIR /usr/src/app
RUN npm install -g pnpm && apk add --no-cache gettext-envsubst git && git init
# Bundle app source
COPY . .
# Install app dependencies
RUN mkdir -p /src/keys && CI=true pnpm install
# Build resources with placeholder config files
RUN touch .env.production && touch src/config.production.json && npm run build
# Expose the port on which the app will run
EXPOSE 3000
#CMD ["/bin/sh", "docker/scripts/start.sh"]
CMD ["npm", "run", "start"]
