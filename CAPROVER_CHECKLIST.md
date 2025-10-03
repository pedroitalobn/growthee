# ✅ Checklist de Deploy CapRover - Growthee

## Pré-Deploy (Configuração)

### 🔧 Arquivos de Configuração
- [x] `captain-definition` - Configuração principal do CapRover
- [x] `docker-compose.caprover.yml` - Definição dos serviços
- [x] `.caprover` - Template de variáveis
- [x] `Dockerfile.prod` - Backend otimizado para produção
- [x] `frontend/Dockerfile.prod` - Frontend otimizado para produção
- [x] `.dockerignore` - Backend
- [x] `frontend/.dockerignore` - Frontend

### 📜 Scripts de Deploy
- [x] `setup-caprover.sh` - Configuração inicial (executável)
- [x] `deploy.sh` - Script de deploy (executável)
- [x] `DEPLOY_CAPROVER.md` - Documentação completa
- [x] `.env.caprover` - Template de variáveis de ambiente

### 🏗️ Estrutura da Aplicação
- [x] Health check endpoint (`/health`) configurado
- [x] Next.js configurado para `output: 'standalone'`
- [x] Prisma configurado para geração automática
- [x] Variáveis de ambiente mapeadas

## Deploy Steps

### 1️⃣ Primeira Configuração
```bash
# 1. Executar setup inicial
./setup-caprover.sh captain.seudominio.com growthee

# 2. Configurar variáveis no painel CapRover
# Ver arquivo .env.caprover para referência
```

### 2️⃣ Deploy da Aplicação
```bash
# Deploy automático
./deploy.sh captain.seudominio.com growthee
```

## Verificações Pós-Deploy

### 🌐 URLs de Acesso
- [ ] Backend: `https://growthee.seudominio.com/health`
- [ ] Frontend: `https://growthee-frontend.seudominio.com`
- [ ] Database: Conectividade interna
- [ ] Redis: Conectividade interna

### 🔍 Testes Funcionais
- [ ] Login/Registro funcionando
- [ ] API endpoints respondendo
- [ ] Integração com Stripe
- [ ] Scraping/Enrichment funcionando
- [ ] Dashboard carregando dados

### 📊 Monitoramento
- [ ] Logs do backend sem erros críticos
- [ ] Logs do frontend sem erros críticos
- [ ] Health checks passando
- [ ] Métricas de performance aceitáveis

## Variáveis de Ambiente Críticas

### Backend (growthee)
```
DATABASE_URL=postgresql://user:pass@srv-captain--growthee-db:5432/growthee
JWT_SECRET_KEY=secure_jwt_secret
STRIPE_SECRET_KEY=sk_live_...
BRAVE_API_KEY=your_api_key
```

### Frontend (growthee-frontend)
```
NEXT_PUBLIC_API_URL=https://growthee.seudominio.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

## Troubleshooting

### 🚨 Problemas Comuns
1. **Build falha**: Verificar logs do Docker build
2. **Database connection**: Verificar DATABASE_URL e conectividade
3. **Frontend não carrega**: Verificar NEXT_PUBLIC_API_URL
4. **API errors**: Verificar variáveis de ambiente e logs

### 📋 Comandos Úteis
```bash
# Ver logs do backend
caprover logs --appName growthee

# Ver logs do frontend
caprover logs --appName growthee-frontend

# Restart aplicação
caprover api --path "/user/apps/appData/growthee" --method POST --data '{"forceSsl":true}'
```

## 🎯 Próximos Passos

1. **SSL**: Configurar certificados SSL automáticos
2. **Backup**: Configurar backup automático do PostgreSQL
3. **Monitoring**: Configurar alertas e monitoramento
4. **CDN**: Configurar CDN para assets estáticos
5. **Scaling**: Configurar auto-scaling se necessário

---

**✅ Deploy Completo**: Quando todos os itens estiverem marcados, sua aplicação Growthee estará rodando em produção no CapRover!