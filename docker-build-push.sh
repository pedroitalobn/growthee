#!/bin/bash

# Script para build e push das imagens Docker para o Docker Hub
# Uso: ./docker-build-push.sh [versao]

set -e

# Configurações
DOCKER_USERNAME="mrstory"
BACKEND_IMAGE="${DOCKER_USERNAME}/growthee-backend"
FRONTEND_IMAGE="${DOCKER_USERNAME}/growthee-frontend"

# Verificar se a versão foi fornecida
if [ -z "$1" ]; then
    echo "❌ Erro: Versão não fornecida"
    echo "Uso: $0 <versao>"
    echo "Exemplo: $0 1.0.0"
    exit 1
fi

VERSION="$1"

echo "🚀 Iniciando build e push das imagens Docker"
echo "📦 Versão: $VERSION"
echo "🐳 Backend: $BACKEND_IMAGE:$VERSION"
echo "🌐 Frontend: $FRONTEND_IMAGE:$VERSION"
echo ""

# Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Inicie o Docker e tente novamente."
    exit 1
fi

# Verificar se está logado no Docker Hub
echo "🔐 Verificando login no Docker Hub..."
if ! docker info | grep -q "Username"; then
    echo "⚠️  Não está logado no Docker Hub. Fazendo login..."
    docker login
fi

# Build da imagem do backend
echo "🔨 Fazendo build da imagem do backend..."
docker build -f Dockerfile.backend.prod -t "$BACKEND_IMAGE:$VERSION" -t "$BACKEND_IMAGE:latest" .

if [ $? -eq 0 ]; then
    echo "✅ Build do backend concluído com sucesso"
else
    echo "❌ Erro no build do backend"
    exit 1
fi

# Build da imagem do frontend
echo "🔨 Fazendo build da imagem do frontend..."
docker build -f Dockerfile.frontend.prod -t "$FRONTEND_IMAGE:$VERSION" -t "$FRONTEND_IMAGE:latest" ./frontend

if [ $? -eq 0 ]; then
    echo "✅ Build do frontend concluído com sucesso"
else
    echo "❌ Erro no build do frontend"
    exit 1
fi

# Push das imagens para o Docker Hub
echo "📤 Fazendo push das imagens para o Docker Hub..."

echo "📤 Pushing backend..."
docker push "$BACKEND_IMAGE:$VERSION"
docker push "$BACKEND_IMAGE:latest"

echo "📤 Pushing frontend..."
docker push "$FRONTEND_IMAGE:$VERSION"
docker push "$FRONTEND_IMAGE:latest"

echo ""
echo "🎉 Build e push concluídos com sucesso!"
echo "📦 Imagens disponíveis:"
echo "   🐳 Backend: $BACKEND_IMAGE:$VERSION"
echo "   🌐 Frontend: $FRONTEND_IMAGE:$VERSION"
echo ""
echo "🚀 Para usar no CapRover:"
echo "   Backend: $BACKEND_IMAGE:$VERSION"
echo "   Frontend: $FRONTEND_IMAGE:$VERSION"
echo ""
echo "💡 Próximos passos:"
echo "   1. Acesse o painel do CapRover"
echo "   2. Vá para as aplicações backend e frontend"
echo "   3. Configure para usar as imagens Docker:"
echo "      - Backend: $BACKEND_IMAGE:$VERSION"
echo "      - Frontend: $FRONTEND_IMAGE:$VERSION"
echo "   4. Configure as variáveis de ambiente necessárias"
echo "   5. Faça o deploy das aplicações"
echo ""
echo "✨ Deploy automatizado concluído!"