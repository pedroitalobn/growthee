# Frontend Next.js
FROM node:18-alpine AS builder

WORKDIR /app

# Instalar dependências necessárias para compilação
RUN apk add --no-cache python3 make g++ git

# Copiar package files
COPY package*.json ./

# Instalar dependências
RUN npm ci

# Copiar código fonte
COPY . .

# Build da aplicação
RUN npm run build

# Produção
FROM node:18-alpine AS runner
WORKDIR /app

# Copiar arquivos do standalone
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Expor porta
EXPOSE 3000

# Comando para iniciar
CMD ["node", "server.js"]