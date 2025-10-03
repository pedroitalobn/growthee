#!/bin/bash

# Script de deploy para CapRover
# Uso: ./deploy.sh <servidor_caprover> <nome_app>

set -e

if [ $# -ne 2 ]; then
    echo "Uso: $0 <servidor_caprover> <nome_app>"
    echo "Exemplo: $0 captain.meuservidor.com growthee"
    exit 1
fi

SERVER=$1
APP_NAME=$2
REGISTRY_URL="registry.$SERVER"

echo "🚀 Iniciando deploy do Growthee para CapRover..."
echo "Servidor: $SERVER"
echo "App: $APP_NAME"
echo "Registry: $REGISTRY_URL"

# Verificar se CapRover CLI está instalado
if ! command -v caprover &> /dev/null; then
    echo "❌ CapRover CLI não encontrado. Instale com: npm install -g caprover"
    exit 1
fi

echo "📦 Construindo e enviando imagens Docker..."

# Build e push da imagem do backend
echo "🔨 Construindo backend..."
docker build -f Dockerfile.prod -t $REGISTRY_URL/$APP_NAME:latest .
echo "📤 Enviando imagem do backend..."
docker push $REGISTRY_URL/$APP_NAME:latest

# Build e push da imagem do frontend
echo "🔨 Construindo frontend..."
cd frontend
docker build -f Dockerfile.prod -t $REGISTRY_URL/$APP_NAME-frontend:latest .
echo "📤 Enviando imagem do frontend..."
docker push $REGISTRY_URL/$APP_NAME-frontend:latest
cd ..

echo "🚢 Fazendo deploy para CapRover..."
caprover deploy --caproverUrl https://$SERVER --appName $APP_NAME

echo "✅ Deploy concluído com sucesso!"
echo "🌐 Backend: https://$APP_NAME.$SERVER"
echo "🌐 Frontend: https://$APP_NAME-frontend.$SERVER"