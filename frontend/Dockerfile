# Frontend Next.js
# Try one of these more stable alternatives:
FROM node:18-slim
# or
FROM node:20-alpine
# or
FROM node:lts-alpine

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependências
RUN npm ci --only=production

# Copiar código fonte
COPY . .

# Definir variáveis de ambiente para build
ENV NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_placeholder

# Build da aplicação
RUN npm run build

# Expor porta
EXPOSE 3000

# Comando para iniciar
CMD ["npm", "start"]