#!/bin/bash

# Setup GitHub Actions for CapRover Deployment
# Este script ajuda a configurar os secrets necessários no GitHub

set -e

echo "🚀 Configuração do GitHub Actions para Deploy CapRover"
echo "================================================="

# Verificar se gh CLI está instalado
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) não encontrado. Instale com:"
    echo "   brew install gh"
    echo "   ou visite: https://cli.github.com/"
    exit 1
fi

# Verificar se está logado no GitHub
if ! gh auth status &> /dev/null; then
    echo "🔐 Fazendo login no GitHub..."
    gh auth login
fi

echo "📝 Configurando secrets do GitHub Actions..."
echo ""

# Solicitar informações do usuário
read -p "🌐 Domínio do CapRover (ex: meuservidor.com): " CAPROVER_DOMAIN
read -p "📱 Nome da aplicação no CapRover (ex: growthee): " APP_NAME
read -s -p "🔑 Senha do CapRover: " CAPROVER_PASSWORD
echo ""

# Configurar secrets
echo "⚙️  Configurando secrets..."

gh secret set CAPROVER_DOMAIN --body "$CAPROVER_DOMAIN"
gh secret set CAPROVER_APP_NAME --body "$APP_NAME"
gh secret set CAPROVER_PASSWORD --body "$CAPROVER_PASSWORD"

echo "✅ Secrets configurados com sucesso!"
echo ""
echo "📋 Secrets configurados:"
echo "   - CAPROVER_DOMAIN: $CAPROVER_DOMAIN"
echo "   - CAPROVER_APP_NAME: $APP_NAME"
echo "   - CAPROVER_PASSWORD: [HIDDEN]"
echo ""
echo "🔧 Próximos passos:"
echo "1. Configure as variáveis de ambiente no painel do CapRover:"
echo "   https://captain.$CAPROVER_DOMAIN"
echo ""
echo "2. Variáveis necessárias para o backend ($APP_NAME-backend):"
echo "   - \$\$cap_postgres_user (ex: growthee_user)"
echo "   - \$\$cap_postgres_password (senha segura)"
echo "   - \$\$cap_jwt_secret (chave JWT segura)"
echo "   - \$\$cap_stripe_secret (sk_live_...)"
echo "   - \$\$cap_stripe_public_key (pk_live_...)"
echo "   - \$\$cap_brave_token (sua chave da API Brave)"
echo ""
echo "3. Faça push para a branch main/master para iniciar o deploy:"
echo "   git add ."
echo "   git commit -m 'feat: add GitHub Actions deploy'"
echo "   git push origin main"
echo ""
echo "4. Acompanhe o deploy em:"
echo "   https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name')/actions"
echo ""
echo "🌐 URLs após o deploy:"
echo "   Frontend: https://$APP_NAME.$CAPROVER_DOMAIN"
echo "   Backend: https://$APP_NAME-backend.$CAPROVER_DOMAIN"
echo "   Health: https://$APP_NAME-backend.$CAPROVER_DOMAIN/health"
echo ""
echo "✨ Configuração concluída! O deploy automático está pronto."