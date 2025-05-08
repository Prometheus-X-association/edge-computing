# Use the official Node.js alpine image as base image
FROM node:23.11.0-alpine3.21
ARG ENV
ENV ENV=$ENV
# Install pnpm globally & Create app directory
WORKDIR /usr/src/app
RUN npm install -g pnpm && apk add --no-cache gettext-envsubst git
# Bundle app source
COPY . .
# Install app dependencies
RUN mkdir -p /src/keys && pnpm install --frozen-lockfile
# Build resources
RUN npm run build
# Expose the port on which the app will run
EXPOSE 3000
#CMD ["/bin/sh", "docker/scripts/start.sh"]
CMD ["npm", "run", "start", "--omit=dev"]
