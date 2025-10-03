# CapRover Deployment Troubleshooting

## Problemas Resolvidos

### 1. Imagens Docker Incorretas
**Problema:** As configurações estavam usando imagens antigas (`pedroitalobn/growthee-*`)
**Solução:** Atualizadas para usar as imagens corretas do Docker Hub:
- `mrstory/growthee-frontend:latest`
- `mrstory/growthee-backend:latest`

### 2. Variáveis de Ambiente Inconsistentes
**Problema:** Nomes de variáveis diferentes entre arquivos
**Solução:** Padronizadas as variáveis:
- `JWT_SECRET_KEY` (não `JWT_SECRET`)
- `BRAVE_API_KEY` (não `BRAVE_SEARCH_API_KEY`)
- Adicionada `STRIPE_PUBLIC_KEY` no backend

### 3. URLs de Serviços Incorretas
**Problema:** URLs de conexão entre serviços mal configuradas
**Solução:** Corrigidas para usar prefixo CapRover:
- Redis: `redis://srv-captain--$$cap_appname-redis:6379`
- Database: `postgresql://$$cap_postgres_user:$$cap_postgres_password@srv-captain--$$cap_appname-db:5432/growthee`
- API URL: `https://$$cap_appname-backend.$$cap_root_domain`

### 4. Dependências e Portas
**Problema:** Dependências e mapeamento de portas incorretos
**Solução:**
- Frontend (porta 3000) depende apenas do backend
- Backend (porta 8000) depende do DB e Redis
- Adicionado `restart: always` em todos os serviços

## Como Fazer o Deploy

1. **Verificar se as imagens estão no Docker Hub:**
   ```bash
   docker pull mrstory/growthee-frontend:latest
   docker pull mrstory/growthee-backend:latest
   ```

2. **Configurar variáveis no CapRover:**
   - `$$cap_postgres_user`
   - `$$cap_postgres_password`
   - `$$cap_jwt_secret`
   - `$$cap_stripe_secret`
   - `$$cap_stripe_public_key`
   - `$$cap_brave_token`

3. **Fazer deploy usando o arquivo corrigido:**
   - Use `docker-compose.caprover.yml` ou `captain-definition`
   - Ambos foram corrigidos com as mesmas configurações

## Verificações Pós-Deploy

1. **Logs dos containers:**
   ```bash
   # No CapRover dashboard, verificar logs de cada serviço
   ```

2. **Conectividade entre serviços:**
   - Backend deve conseguir conectar ao PostgreSQL
   - Backend deve conseguir conectar ao Redis
   - Frontend deve conseguir fazer requests para o backend

3. **Variáveis de ambiente:**
   - Verificar se todas as variáveis estão definidas
   - Testar endpoints da API

## Comandos Úteis

```bash
# Rebuild e redeploy
caprover deploy --caproverUrl https://captain.yourdomain.com --appToken YOUR_TOKEN

# Verificar status dos serviços
docker ps
docker logs CONTAINER_ID
```