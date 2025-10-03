#!/bin/bash

# Script de configuração inicial do CapRover
# Uso: ./setup-caprover.sh <servidor_caprover> <nome_app>

set -e

if [ $# -ne 2 ]; then
    echo "Uso: $0 <servidor_caprover> <nome_app>"
    echo "Exemplo: $0 captain.meuservidor.com growthee"
    exit 1
fi

SERVER=$1
APP_NAME=$2

echo "⚙️  Configurando CapRover para o Growthee..."
echo "Servidor: $SERVER"
echo "App: $APP_NAME"

# Verificar se CapRover CLI está instalado
if ! command -v caprover &> /dev/null; then
    echo "❌ CapRover CLI não encontrado. Instale com: npm install -g caprover"
    exit 1
fi

echo "🔐 Fazendo login no CapRover..."
echo "Digite a senha do CapRover quando solicitado:"
caprover login --caproverUrl https://$SERVER

echo "📱 Criando aplicações no CapRover..."

# Criar app principal (backend)
echo "Criando app backend: $APP_NAME"
caprover api --caproverUrl https://$SERVER --path "/user/apps/appDefinitions" --method POST --data '{"appName":"'$APP_NAME'","hasPersistentData":false}' || echo "App $APP_NAME já existe"

# Criar app frontend
echo "Criando app frontend: $APP_NAME-frontend"
caprover api --caproverUrl https://$SERVER --path "/user/apps/appDefinitions" --method POST --data '{"appName":"'$APP_NAME'-frontend","hasPersistentData":false}' || echo "App $APP_NAME-frontend já existe"

# Criar app database
echo "Criando app database: $APP_NAME-db"
caprover api --caproverUrl https://$SERVER --path "/user/apps/appDefinitions" --method POST --data '{"appName":"'$APP_NAME'-db","hasPersistentData":true}' || echo "App $APP_NAME-db já existe"

# Criar app redis
echo "Criando app redis: $APP_NAME-redis"
caprover api --caproverUrl https://$SERVER --path "/user/apps/appDefinitions" --method POST --data '{"appName":"'$APP_NAME'-redis","hasPersistentData":true}' || echo "App $APP_NAME-redis já existe"

echo "🗄️  Configurando PostgreSQL..."
# Deploy PostgreSQL
caprover api --caproverUrl https://$SERVER --path "/user/apps/appData/$APP_NAME-db" --method POST --data '{
  "captainDefinitionContent": "{\"schemaVersion\":2,\"imageName\":\"postgres:15\"}",
  "envVars": [
    {"key": "POSTGRES_DB", "value": "growthee"},
    {"key": "POSTGRES_USER", "value": "growthee_user"},
    {"key": "POSTGRES_PASSWORD", "value": "'$(openssl rand -base64 32)'"}
  ],
  "volumes": [
    {"containerPath": "/var/lib/postgresql/data", "volumeName": "'$APP_NAME'-db-data"}
  ]
}'

echo "🔴 Configurando Redis..."
# Deploy Redis
caprover api --caproverUrl https://$SERVER --path "/user/apps/appData/$APP_NAME-redis" --method POST --data '{
  "captainDefinitionContent": "{\"schemaVersion\":2,\"imageName\":\"redis:7-alpine\"}",
  "volumes": [
    {"containerPath": "/data", "volumeName": "'$APP_NAME'-redis-data"}
  ]
}'

echo "✅ Configuração inicial concluída!"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure as variáveis de ambiente no painel do CapRover:"
echo "   - DATABASE_URL"
echo "   - JWT_SECRET"
echo "   - STRIPE_PUBLIC_KEY"
echo "   - STRIPE_SECRET_KEY"
echo "   - BRAVE_SEARCH_API_KEY"
echo ""
echo "2. Execute o deploy com: ./deploy.sh $SERVER $APP_NAME"
echo ""
echo "🌐 Painel CapRover: https://$SERVER"
echo "🌐 Backend: https://$APP_NAME.$SERVER"
echo "🌐 Frontend: https://$APP_NAME-frontend.$SERVER"