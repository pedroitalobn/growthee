# Deploy Automático via GitHub Actions

Este guia explica como configurar deploy automático da aplicação Growthee no CapRover usando GitHub Actions.

## 🚀 Configuração Rápida

### 1. Executar Script de Configuração

```bash
./setup-github-actions.sh
```

Este script irá:
- Verificar se o GitHub CLI está instalado
- Configurar os secrets necessários no repositório
- Fornecer instruções para os próximos passos

### 2. Configurar Variáveis no CapRover

No painel do CapRover (`https://captain.seudominio.com`), configure as seguintes variáveis:

**Para o backend (`growthee-backend`):**
```
$$cap_postgres_user=growthee_user
$$cap_postgres_password=senha_super_segura
$$cap_jwt_secret=chave_jwt_muito_segura_com_32_chars
$$cap_stripe_secret=sk_live_sua_chave_stripe
$$cap_stripe_public_key=pk_live_sua_chave_publica_stripe
$$cap_brave_token=sua_chave_api_brave
```

### 3. Fazer Deploy

```bash
git add .
git commit -m "feat: add GitHub Actions deploy"
git push origin main
```

O deploy será executado automaticamente!

## 📋 Secrets do GitHub

Os seguintes secrets são configurados automaticamente pelo script:

| Secret | Descrição | Exemplo |
|--------|-----------|----------|
| `CAPROVER_DOMAIN` | Domínio do seu CapRover | `meuservidor.com` |
| `CAPROVER_APP_NAME` | Nome da aplicação | `growthee` |
| `CAPROVER_PASSWORD` | Senha do CapRover | `[HIDDEN]` |

## 🔧 Configuração Manual (Alternativa)

Se preferir configurar manualmente:

### 1. Instalar GitHub CLI

```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh

# Windows
winget install GitHub.cli
```

### 2. Fazer Login

```bash
gh auth login
```

### 3. Configurar Secrets

```bash
gh secret set CAPROVER_DOMAIN --body "seudominio.com"
gh secret set CAPROVER_APP_NAME --body "growthee"
gh secret set CAPROVER_PASSWORD --body "sua_senha_caprover"
```

## 🏗️ Como Funciona o Workflow

O arquivo `.github/workflows/deploy-caprover.yml` executa:

1. **Build das Imagens Docker**
   - Backend: `Dockerfile.backend.ultra-fast`
   - Frontend: `frontend/Dockerfile.prod`

2. **Push para Registry do CapRover**
   - Imagens são enviadas para `registry.captain.seudominio.com`
   - Tags: `latest` e `commit-sha`

3. **Deploy Automático**
   - Cria configuração dinâmica do docker-compose
   - Faz deploy via CapRover CLI
   - Verifica se o deploy foi bem-sucedido

## 🎯 Triggers do Deploy

O deploy é executado automaticamente quando:
- Push para branch `main` ou `master`
- Execução manual via GitHub Actions UI

## 📊 Monitoramento

### URLs Após Deploy
- **Frontend**: `https://growthee.seudominio.com`
- **Backend**: `https://growthee-backend.seudominio.com`
- **Health Check**: `https://growthee-backend.seudominio.com/health`

### Logs do Deploy
- Acesse: `https://github.com/seu-usuario/growthee/actions`
- Clique no workflow mais recente
- Visualize logs detalhados de cada etapa

## 🔍 Troubleshooting

### Erro: "Registry login failed"
```bash
# Verificar se a senha do CapRover está correta
gh secret set CAPROVER_PASSWORD --body "nova_senha"
```

### Erro: "App not found"
```bash
# Verificar se o nome da app está correto
gh secret set CAPROVER_APP_NAME --body "nome_correto"
```

### Erro: "Docker build failed"
- Verificar se os Dockerfiles existem
- Verificar se as dependências estão corretas
- Verificar logs detalhados no GitHub Actions

### Erro: "Deploy timeout"
- Verificar se o CapRover está acessível
- Verificar se as variáveis de ambiente estão configuradas
- Tentar deploy manual para debug

## 🚀 Otimizações

### Cache do Docker
- O workflow usa cache do GitHub Actions
- Builds subsequentes são mais rápidos
- Cache é compartilhado entre branches

### Multi-platform Build
- Atualmente configurado para `linux/amd64`
- Pode ser expandido para ARM se necessário

### Rollback Automático
- Em caso de falha, o CapRover mantém a versão anterior
- Para rollback manual, use o painel do CapRover

## 📈 Próximos Passos

1. **Configurar Staging**: Criar ambiente de teste
2. **Testes Automáticos**: Adicionar testes antes do deploy
3. **Notificações**: Configurar Slack/Discord para notificações
4. **Monitoramento**: Integrar com Sentry/DataDog

---

**✅ Deploy Automático Configurado!** 
Agora toda alteração na branch main será automaticamente deployada no CapRover.