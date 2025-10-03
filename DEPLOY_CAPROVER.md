# Deploy do Growthee no CapRover

Este guia explica como fazer o deploy da aplicação Growthee em um servidor CapRover.

## Pré-requisitos

1. **Servidor CapRover configurado**
   - CapRover instalado e funcionando
   - Domínio configurado
   - SSL habilitado

2. **CapRover CLI instalado localmente**
   ```bash
   npm install -g caprover
   ```

3. **Docker instalado localmente**
   - Para build das imagens

4. **Credenciais necessárias**
   - URL do servidor CapRover
   - Senha de admin do CapRover
   - Chaves da API (Stripe, Brave Search, etc.)

## Configuração Inicial (Primeira vez)

### 1. Executar script de configuração

```bash
./setup-caprover.sh <servidor_caprover> <nome_app>
```

Exemplo:
```bash
./setup-caprover.sh captain.meuservidor.com growthee
```

Este script irá:
1. Fazer login no CapRover
2. Criar todas as aplicações necessárias
3. Configurar PostgreSQL e Redis
4. Preparar a estrutura básica

### 2. Configurar variáveis de ambiente

No painel do CapRover, configure as variáveis para cada aplicação:

**Backend (growthee):**
- `DATABASE_URL`: `postgresql://growthee_user:senha@srv-captain--growthee-db:5432/growthee`
- `JWT_SECRET`: Chave secreta para JWT
- `STRIPE_PUBLIC_KEY`: Chave pública do Stripe
- `STRIPE_SECRET_KEY`: Chave secreta do Stripe
- `BRAVE_SEARCH_API_KEY`: Token da API Brave Search

**Frontend (growthee-frontend):**
- `NEXT_PUBLIC_API_URL`: `https://growthee.seudominio.com`

## Deploy Automático

### Usando o script de deploy

```bash
./deploy.sh <servidor_caprover> <nome_app>
```

Exemplo:
```bash
./deploy.sh captain.meuservidor.com growthee
```

O script irá:
1. Verificar se o CapRover CLI está instalado
2. Fazer build das imagens Docker
3. Fazer push para o registry do CapRover
4. Executar o deploy

## Deploy Manual

### 1. Build das imagens

**Backend:**
```bash
docker build -f Dockerfile.prod -t registry.captain.seudominio.com/growthee:latest .
docker push registry.captain.seudominio.com/growthee:latest
```

**Frontend:**
```bash
cd frontend
docker build -f Dockerfile.prod -t registry.captain.seudominio.com/growthee-frontend:latest .
docker push registry.captain.seudominio.com/growthee-frontend:latest
cd ..
```

### 2. Deploy via CLI

```bash
caprover deploy --caproverUrl https://captain.seudominio.com --appName growthee
```

## Configuração de Variáveis

No painel do CapRover, configure as seguintes variáveis:

- `$$cap_postgres_user`: Usuário PostgreSQL
- `$$cap_postgres_password`: Senha PostgreSQL  
- `$$cap_jwt_secret`: Chave secreta JWT
- `$$cap_stripe_secret`: Chave secreta Stripe
- `$$cap_stripe_public_key`: Chave pública Stripe
- `$$cap_brave_token`: Token API Brave Search

## Estrutura dos Serviços

- **Frontend**: `$$cap_appname` (porta 80)
- **Backend**: `$$cap_appname-backend` (porta 8000)
- **Redis**: `$$cap_appname-redis` (porta 6379)
- **PostgreSQL**: `$$cap_appname-db` (porta 5432)

## Verificação

Após o deploy:

1. Acesse `https://growthee.yourdomain.com`
2. Verifique logs nos serviços
3. Teste funcionalidades principais

## Troubleshooting

### Erro de conexão com banco
- Verificar se PostgreSQL está rodando
- Confirmar variáveis de ambiente

### Erro de build
- Verificar se imagens estão no registry
- Confirmar tags das imagens

### Erro de memória
- Aumentar recursos do servidor
- Otimizar configurações Docker