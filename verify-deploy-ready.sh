#!/bin/bash

# Script de Verificação Completa para Deploy
# Verifica se todos os arquivos e configurações estão prontos

set -e

echo "🔍 Verificação Completa para Deploy - Growthee"
echo "============================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
PASSED=0
FAILED=0
WARNINGS=0

# Função para verificar arquivos
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ $1${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ $1 (FALTANDO)${NC}"
        ((FAILED++))
        return 1
    fi
}

# Função para verificar diretórios
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅ $1/${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ $1/ (FALTANDO)${NC}"
        ((FAILED++))
        return 1
    fi
}

# Função para avisos
warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

# Função para info
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo "📁 Verificando Estrutura de Arquivos..."
echo "======================================"

# Arquivos essenciais do backend
echo "🔧 Backend:"
check_file "requirements-minimal.txt"
check_file "Dockerfile.backend.ultra-fast"
check_file "Dockerfile.backend.micro"
check_file "prisma/schema.prisma"
check_file "api/main.py"

# Arquivos essenciais do frontend
echo "
🎨 Frontend:"
check_file "frontend/package.json"
check_file "frontend/next.config.js"
check_file "frontend/Dockerfile.prod"
check_dir "frontend/app"
check_dir "frontend/components"

# Configurações de deploy
echo "
🚀 Deploy:"
check_file "captain-definition"
check_file "docker-compose.caprover.yml"
check_file ".caprover"
check_file ".env.caprover"
check_file "deploy-ultra-fast.sh"
check_file "setup-caprover.sh"
check_file "deploy.sh"

# GitHub Actions
echo "
🤖 GitHub Actions:"
check_file ".github/workflows/deploy-caprover.yml"
check_file "setup-github-actions.sh"
check_file "DEPLOY_GITHUB_ACTIONS.md"

# Dockerignore files
echo "
🐳 Docker:"
check_file ".dockerignore.ultra"
if [ -f "frontend/.dockerignore" ]; then
    echo -e "${GREEN}✅ frontend/.dockerignore${NC}"
    ((PASSED++))
else
    warn "frontend/.dockerignore não encontrado (recomendado)"
fi

echo "
🔍 Verificando Configurações..."
echo "=============================="

# Verificar next.config.js
if grep -q "output: 'standalone'" frontend/next.config.js; then
    echo -e "${GREEN}✅ Next.js configurado para standalone${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Next.js não configurado para standalone${NC}"
    ((FAILED++))
fi

# Verificar captain-definition
if grep -q "Dockerfile.backend.ultra-fast" captain-definition; then
    echo -e "${GREEN}✅ captain-definition usando Dockerfile otimizado${NC}"
    ((PASSED++))
elif grep -q "Dockerfile.backend.micro" captain-definition; then
    echo -e "${YELLOW}⚠️  captain-definition usando Dockerfile.backend.micro (OK, mas ultra-fast é melhor)${NC}"
    ((WARNINGS++))
else
    echo -e "${RED}❌ captain-definition não configurado corretamente${NC}"
    ((FAILED++))
fi

# Verificar se scripts são executáveis
echo "
🔧 Verificando Permissões..."
echo "============================"
for script in "deploy-ultra-fast.sh" "setup-caprover.sh" "deploy.sh" "setup-github-actions.sh" "verify-deploy-ready.sh"; do
    if [ -x "$script" ]; then
        echo -e "${GREEN}✅ $script (executável)${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️  $script (não executável - execute: chmod +x $script)${NC}"
        ((WARNINGS++))
    fi
done

echo "
📊 Verificando Dependências..."
echo "=============================="

# Verificar Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✅ Node.js $NODE_VERSION${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Node.js não instalado${NC}"
    ((FAILED++))
fi

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Python3 não instalado${NC}"
    ((FAILED++))
fi

# Verificar Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✅ $DOCKER_VERSION${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Docker não instalado${NC}"
    ((FAILED++))
fi

# Verificar GitHub CLI (opcional)
if command -v gh &> /dev/null; then
    GH_VERSION=$(gh --version | head -n1)
    echo -e "${GREEN}✅ $GH_VERSION${NC}"
    ((PASSED++))
else
    warn "GitHub CLI não instalado (necessário para GitHub Actions)"
fi

echo "
📋 Resumo da Verificação"
echo "======================="
echo -e "${GREEN}✅ Passou: $PASSED${NC}"
if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Avisos: $WARNINGS${NC}"
fi
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ Falhou: $FAILED${NC}"
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 TUDO PRONTO PARA DEPLOY!${NC}"
    echo ""
    echo "📋 Opções de Deploy:"
    echo ""
    echo "1️⃣  Deploy via CapRover (Docker):"
    echo "   ./deploy-ultra-fast.sh"
    echo ""
    echo "2️⃣  Deploy via GitHub Actions:"
    echo "   ./setup-github-actions.sh"
    echo "   git add . && git commit -m 'deploy' && git push"
    echo ""
    echo "3️⃣  Deploy manual via CapRover CLI:"
    echo "   ./deploy.sh captain.seudominio.com growthee"
    echo ""
    echo -e "${BLUE}💡 Recomendação: Use GitHub Actions para deploy automático!${NC}"
else
    echo -e "${RED}❌ CORRIJA OS ERROS ANTES DO DEPLOY${NC}"
    echo ""
    echo "🔧 Ações necessárias:"
    if [ $FAILED -gt 0 ]; then
        echo "   - Corrija os arquivos faltando marcados com ❌"
    fi
    if [ $WARNINGS -gt 0 ]; then
        echo "   - Considere resolver os avisos marcados com ⚠️"
    fi
fi

echo ""
echo "📚 Documentação:"
echo "   - CapRover: DEPLOY_CAPROVER.md"
echo "   - GitHub Actions: DEPLOY_GITHUB_ACTIONS.md"
echo "   - Troubleshooting: CAPROVER_TROUBLESHOOTING.md"
echo ""

exit $FAILED