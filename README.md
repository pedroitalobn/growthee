# Growthee SaaS

Plataforma SaaS para enriquecimento de dados de empresas e pessoas usando LinkedIn e Brave Search.

## 🚀 Features

- **Autenticação JWT** com sistema de créditos
- **Enriquecimento de Empresas** via LinkedIn e Brave Search
- **Enriquecimento de Pessoas** com dados profissionais
- **Sistema de Billing** integrado com Stripe
- **Dashboard Administrativo** para gestão
- **API Endpoints Customizados** para usuários premium
- **Frontend Moderno** em Next.js 14

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Framework web moderno
- **PostgreSQL** - Banco de dados principal
- **Redis** - Cache e sessões
- **Prisma** - ORM
- **Playwright** - Web scraping
- **Stripe** - Pagamentos

### Frontend
- **Next.js 14** - Framework React
- **TypeScript** - Tipagem estática
- **Tailwind CSS** - Estilização
- **Shadcn/ui** - Componentes UI
- **Zustand** - Gerenciamento de estado
- **React Query** - Cache de dados

## 🐳 Deploy com Docker

### Desenvolvimento Local
```bash
# Clone o repositório
git clone https://github.com/pedroitalobn/growthee.git
cd growthee

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas configurações

# Execute com Docker Compose
docker-compose up -d
```

### Produção
```bash
# Backend
docker pull pedroitalobn/growthee-backend:latest

# Frontend
docker pull pedroitalobn/growthee-frontend:latest

# Execute o docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d
```

## 📝 Configuração

### Variáveis de Ambiente Obrigatórias
```env
DATABASE_URL=postgresql://user:password@localhost:5432/growthee
REDIS_URL=redis://localhost:6379
JWT_SECRET=sua_chave_super_secreta
STRIPE_SECRET_KEY=sk_...
LINKEDIN_EMAIL=seu_email
LINKEDIN_PASSWORD=sua_senha
BRAVE_API_KEY=sua_chave_brave
```

## 🔗 Endpoints da API

- `GET /health` - Health check
- `POST /auth/login` - Login
- `POST /auth/register` - Registro
- `POST /enrich/company` - Enriquecer empresa
- `POST /enrich/person` - Enriquecer pessoa
- `GET /dashboard/stats` - Estatísticas do usuário
- `GET /docs` - Documentação Swagger

## 📊 Monitoramento

- **Logs**: Centralizados via Docker
- **Métricas**: Prometheus + Grafana
- **Errors**: Sentry integration

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Add nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

MIT License