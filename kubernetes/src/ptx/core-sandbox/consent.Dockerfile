FROM node:18-alpine
WORKDIR /usr/src/app
COPY ./utils/consent/app.js ./utils/consent/package.json ./
RUN npm install
EXPOSE 8083
CMD ["node", "app.js"]