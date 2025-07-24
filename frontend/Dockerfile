# Frontend
FROM node:18-alpine

WORKDIR /app

# Copiar package files
COPY package*.json ./
RUN npm ci --only=production

# Copiar código
COPY . .

# Build
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]